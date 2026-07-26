"""OpenAI (ChatGPT) adapter — raw REST via httpx (no SDK dependency)."""

from __future__ import annotations

import httpx

from app.agent.llm.base import LLMClient, LLMError, LLMResponse, call_with_retry, extract_json

_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIClient(LLMClient):
    provider = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate_json(self, system: str, user: str, *, temperature: float, max_tokens: int) -> LLMResponse:
        def _do() -> LLMResponse:
            try:
                resp = httpx.post(
                    _URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    },
                    timeout=60.0,
                )
            except httpx.HTTPError as exc:
                raise LLMError(f"network error: {exc}", retryable=True) from exc

            if resp.status_code == 429 or resp.status_code >= 500:
                raise LLMError(f"openai {resp.status_code}: {resp.text[:200]}", retryable=True)
            if resp.status_code >= 400:
                raise LLMError(f"openai {resp.status_code}: {resp.text[:200]}", retryable=False)

            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            data = extract_json(content)
            return LLMResponse(data=data, usage=body.get("usage", {}))

        return call_with_retry(_do)
