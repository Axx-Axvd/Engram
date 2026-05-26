"""Select the LLM provider from configuration (cached for the process)."""

from __future__ import annotations

from functools import lru_cache

from engram.config import settings
from engram.llm.base import LLMProvider
from engram.llm.mock import MockLLMProvider


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    name = settings.llm_provider.lower()
    if name == "mock":
        return MockLLMProvider()
    # Real providers (anthropic / openai) are added in a later milestone.
    raise ValueError(f"Unknown or unsupported LLM provider: {settings.llm_provider!r}")
