"""Application settings, loaded from environment / repo-root `.env` with the `ENGRAM_` prefix."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at: <repo>/apps/api/src/engram/config.py  → repo root is 4 parents up.
_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_prefix="ENGRAM_",
        extra="ignore",
    )

    # Database (PostgreSQL + pgvector).
    db_url: str = "postgresql+psycopg://engram:engram@localhost:5432/engram"

    # Provider selection (see engram.llm / engram.embeddings factories).
    llm_provider: str = "mock"
    embedding_provider: str = "local"
    embedding_dim: int = 384

    # CORS: comma-separated list of allowed origins.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
