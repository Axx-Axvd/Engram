"""Deterministic, dependency-free embeddings via signed feature hashing.

No semantics, but lexical overlap produces vector overlap — enough to exercise and test
similarity search offline and with stable results.
"""

from __future__ import annotations

import hashlib
import math
import re

from engram.embeddings.base import EmbeddingProvider

_TOKEN_RE = re.compile(r"[0-9a-zA-Zа-яёА-ЯЁ]+")


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int = 384) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            h = int.from_bytes(digest[:8], "big")
            idx = h % self._dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec
