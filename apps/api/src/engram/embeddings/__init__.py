"""Embedding providers — turn artifact text into vectors for similarity search."""

from engram.embeddings.base import EmbeddingProvider
from engram.embeddings.factory import get_embedding_provider

__all__ = ["EmbeddingProvider", "get_embedding_provider"]
