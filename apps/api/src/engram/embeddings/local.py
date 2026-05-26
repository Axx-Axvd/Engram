"""Local embeddings via fastembed (ONNX). Lazy-imported so the dependency is optional."""

from __future__ import annotations

from functools import cached_property

from engram.embeddings.base import EmbeddingProvider

_DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"  # 384-dimensional


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int = 384, model_name: str = _DEFAULT_MODEL) -> None:
        self._dim = dim
        self._model_name = model_name

    @property
    def dim(self) -> int:
        return self._dim

    @cached_property
    def _model(self):  # noqa: ANN202 - fastembed type is optional
        try:
            from fastembed import TextEmbedding
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError(
                "Local embeddings require fastembed. Install it with: uv sync --extra local"
            ) from exc
        return TextEmbedding(model_name=self._model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in vector] for vector in self._model.embed(texts)]
