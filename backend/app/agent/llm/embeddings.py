"""Embedding clients — text → vector, provider-agnostic.

Same seam pattern as ``LLMClient``: the RAG code depends on ``EmbeddingClient``,
never on a specific provider.
"""

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod

import httpx

from app.agent.llm.base import LLMError, call_with_retry
from app.core.config import settings

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_OPENAI_URL = "https://api.openai.com/v1/embeddings"


def _l2_normalize(vec: list[float]) -> list[float]:
    """Scale to unit length so cosine similarity behaves as expected.

    Gemini only returns normalized vectors at full dimensionality; truncated
    (outputDimensionality < 3072) vectors must be normalized by the caller.
    """
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec


class EmbeddingClient(ABC):
    provider: str = ""
    model: str = ""
    dim: int = 0

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Raises ``LLMError`` on failure."""


class GeminiEmbeddingClient(EmbeddingClient):
    provider = "gemini"

    def __init__(self, api_key: str, model: str, dim: int) -> None:
        self.api_key = api_key
        self.model = model
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        url = f"{_GEMINI_BASE}/{self.model}:batchEmbedContents"
        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": t}]},
                    "outputDimensionality": self.dim,
                }
                for t in texts
            ]
        }

        def _do() -> list[list[float]]:
            try:
                resp = httpx.post(url, params={"key": self.api_key}, json=payload, timeout=120.0)
            except httpx.HTTPError as exc:
                raise LLMError(f"network error: {exc}", retryable=True) from exc
            if resp.status_code == 429 or resp.status_code >= 500:
                raise LLMError(f"gemini embed {resp.status_code}: {resp.text[:200]}", retryable=True)
            if resp.status_code >= 400:
                raise LLMError(f"gemini embed {resp.status_code}: {resp.text[:200]}", retryable=False)
            try:
                return [_l2_normalize(e["values"]) for e in resp.json()["embeddings"]]
            except (KeyError, TypeError) as exc:
                raise LLMError(f"gemini embed: unexpected response: {exc}", retryable=True) from exc

        return call_with_retry(_do)


class OpenAIEmbeddingClient(EmbeddingClient):
    provider = "openai"

    def __init__(self, api_key: str, model: str, dim: int) -> None:
        self.api_key = api_key
        self.model = model
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _do() -> list[list[float]]:
            try:
                resp = httpx.post(
                    _OPENAI_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": texts, "dimensions": self.dim},
                    timeout=120.0,
                )
            except httpx.HTTPError as exc:
                raise LLMError(f"network error: {exc}", retryable=True) from exc
            if resp.status_code == 429 or resp.status_code >= 500:
                raise LLMError(f"openai embed {resp.status_code}: {resp.text[:200]}", retryable=True)
            if resp.status_code >= 400:
                raise LLMError(f"openai embed {resp.status_code}: {resp.text[:200]}", retryable=False)
            data = sorted(resp.json()["data"], key=lambda d: d["index"])
            return [_l2_normalize(d["embedding"]) for d in data]

        return call_with_retry(_do)


def get_embedding_client() -> EmbeddingClient | None:
    """Build the configured embedding client, or None if unavailable."""
    provider = (settings.embedding_provider or "none").lower()
    if provider == "gemini":
        if not settings.gemini_api_key:
            logger.warning("EMBEDDING_PROVIDER=gemini but GEMINI_API_KEY is not set")
            return None
        return GeminiEmbeddingClient(settings.gemini_api_key, settings.embedding_model, settings.embedding_dim)
    if provider == "openai":
        if not settings.openai_api_key:
            logger.warning("EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set")
            return None
        return OpenAIEmbeddingClient(settings.openai_api_key, settings.embedding_model, settings.embedding_dim)
    if provider not in ("none", ""):
        logger.warning("Unknown EMBEDDING_PROVIDER=%r", provider)
    return None
