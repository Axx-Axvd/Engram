"""Select the embedding provider from configuration (cached for the process)."""

from __future__ import annotations

from functools import lru_cache

from engram.config import settings
from engram.embeddings.base import EmbeddingProvider
from engram.embeddings.mock import MockEmbeddingProvider


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    name = settings.embedding_provider.lower()
    if name == "mock":
        return MockEmbeddingProvider(settings.embedding_dim)
    if name == "local":
        from engram.embeddings.local import LocalEmbeddingProvider

        return LocalEmbeddingProvider(settings.embedding_dim)
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider!r}")
