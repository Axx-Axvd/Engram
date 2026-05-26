"""FastAPI application factory for the Engram backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from engram import __version__
from engram.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Engram API",
        version=__version__,
        description="Project-memory platform: connected, versioned artifacts with context search.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "engram-api", "version": __version__}

    # Domain routers (artifacts, links, search, workflows, consistency) are mounted here in
    # later milestones.

    return app


app = create_app()
