"""LLM provider factory.

``get_llm_client()`` returns the configured provider adapter, or ``None`` if no
provider/key is configured (the caller then falls back to the deterministic stub).
"""

from __future__ import annotations

import logging

from app.agent.llm.base import LLMClient, LLMError, LLMResponse
from app.agent.llm.gemini_client import GeminiClient
from app.agent.llm.openai_client import OpenAIClient
from app.core.config import settings

logger = logging.getLogger(__name__)

__all__ = ["LLMClient", "LLMError", "LLMResponse", "get_llm_client"]


def get_llm_client() -> LLMClient | None:
    provider = (settings.llm_provider or "none").lower()
    if provider == "openai":
        if not settings.openai_api_key:
            logger.warning("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
            return None
        return OpenAIClient(settings.openai_api_key, settings.openai_model)
    if provider == "gemini":
        if not settings.gemini_api_key:
            logger.warning("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set")
            return None
        # Primary model first, then fallbacks (deduped, order preserved).
        candidates = [settings.gemini_model] + [
            m.strip() for m in (settings.gemini_fallback_models or "").split(",") if m.strip()
        ]
        seen: set[str] = set()
        models = [m for m in candidates if m and not (m in seen or seen.add(m))]
        return GeminiClient(settings.gemini_api_key, models)
    if provider not in ("none", ""):
        logger.warning("Unknown LLM_PROVIDER=%r; running without an LLM", provider)
    return None
