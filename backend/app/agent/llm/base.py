"""LLM client contract — the provider-agnostic seam.

Adapters (OpenAI, Gemini, ...) implement ``generate_json``; the orchestrator/tools
never import a specific provider. Mirrors the ``Tool`` interface pattern.
"""

from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def extract_json(text: str) -> dict:
    """Parse a JSON object from an LLM response, tolerating fences/trailing text.

    LLMs sometimes wrap JSON in ```code fences``` or append extra prose even in
    JSON mode. We strip fences, then fall back to decoding the first ``{...}`` object
    (ignoring anything after it). Raises a retryable ``LLMError`` if nothing parses.
    """
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        start = s.find("{")
        if start == -1:
            raise LLMError("no JSON object found in model response", retryable=True)
        try:
            obj, _ = json.JSONDecoder().raw_decode(s[start:])
        except json.JSONDecodeError as exc:
            raise LLMError(f"could not parse JSON from model: {exc}", retryable=True) from exc
    if not isinstance(obj, dict):
        raise LLMError("model JSON was not an object", retryable=True)
    return obj


class LLMError(Exception):
    """Raised on any LLM failure. ``retryable`` marks transient errors (429/5xx/timeout)."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass
class LLMResponse:
    data: dict
    usage: dict = field(default_factory=dict)


class LLMClient(ABC):
    provider: str = ""
    model: str = ""

    @abstractmethod
    def generate_json(
        self, system: str, user: str, *, temperature: float, max_tokens: int
    ) -> LLMResponse:
        """Call the model and return parsed JSON. Raises ``LLMError`` on failure."""


def call_with_retry(fn: Callable[[], T], *, attempts: int = 3, base_delay: float = 1.0) -> T:
    """Run ``fn``, retrying transient ``LLMError``s with exponential backoff."""
    for i in range(attempts):
        try:
            return fn()
        except LLMError as exc:
            if not exc.retryable or i == attempts - 1:
                raise
            delay = base_delay * (2**i)
            logger.warning("LLM call failed (%s); retrying in %.1fs", exc, delay)
            time.sleep(delay)
    raise LLMError("exhausted retries")  # pragma: no cover
