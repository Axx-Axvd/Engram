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
    # Default port 5433 matches the dev Postgres published by infra/docker-compose.yml.
    db_url: str = "postgresql+psycopg://engram:engram@localhost:5433/engram"

    # Provider selection (see engram.llm / engram.embeddings factories).
    # llm_provider: "mock" (default, offline/deterministic) or "claude_code" (subscription-auth
    # Claude CLI via the Agent SDK; needs the `llm` extra). llm_model is an optional override
    # (None = the plan's default model).
    # embedding_provider: "mock" (default, offline) or "local" (fastembed; needs the `local` extra).
    llm_provider: str = "mock"
    llm_model: str | None = None
    embedding_provider: str = "mock"
    embedding_dim: int = 384

    # CORS: comma-separated list of allowed origins.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
