"""Google Gemini adapter — raw REST via httpx (no SDK dependency).

Supports **model failover**: Gemini frequently returns 503 ("model experiencing high
demand") or 429 on a given model while others are fine. We try the primary model, then
each configured fallback, before giving up.
"""

from __future__ import annotations

import logging

import httpx

from app.agent.llm.base import LLMClient, LLMError, LLMResponse, call_with_retry, extract_json

logger = logging.getLogger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient(LLMClient):
    provider = "gemini"

    def __init__(self, api_key: str, models: list[str]) -> None:
        self.api_key = api_key
        self.models = [m for m in models if m]
        # Updated to whichever model actually served the request.
        self.model = self.models[0] if self.models else ""

    def generate_json(self, system: str, user: str, *, temperature: float, max_tokens: int) -> LLMResponse:
        last_error: LLMError | None = None
        for model in self.models:
            try:
                resp = call_with_retry(
                    lambda m=model: self._call(m, system, user, temperature, max_tokens),
                    attempts=2,
                )
                self.model = model
                return resp
            except LLMError as exc:
                last_error = exc
                if not exc.retryable:
                    raise  # e.g. bad key / bad request — trying another model won't help
                logger.warning("Gemini model %s unavailable (%s); trying next model", model, exc)
        raise last_error or LLMError("no gemini model available", retryable=True)

    def _call(self, model: str, system: str, user: str, temperature: float, max_tokens: int) -> LLMResponse:
        url = f"{_BASE}/{model}:generateContent"
        try:
            resp = httpx.post(
                url,
                params={"key": self.api_key},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"parts": [{"text": user}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=60.0,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"network error: {exc}", retryable=True) from exc

        if resp.status_code == 429 or resp.status_code >= 500:
            raise LLMError(f"gemini {resp.status_code} ({model}): {resp.text[:160]}", retryable=True)
        if resp.status_code == 404:
            # Unknown/retired model — treat as retryable so we fall through to the next one.
            raise LLMError(f"gemini 404 ({model}): {resp.text[:160]}", retryable=True)
        if resp.status_code >= 400:
            raise LLMError(f"gemini {resp.status_code} ({model}): {resp.text[:160]}", retryable=False)

        body = resp.json()
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"gemini: unexpected response shape: {exc}", retryable=True) from exc
        return LLMResponse(data=extract_json(text), usage=body.get("usageMetadata", {}))
