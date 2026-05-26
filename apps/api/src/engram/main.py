"""FastAPI application factory for the Engram backend."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from engram import __version__
from engram.api import artifacts, links, search, workflows
from engram.config import settings
from engram.errors import ConflictError, NotFoundError, ValidationError

_ERROR_STATUS: dict[type[Exception], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _make_error_handler(
    status_code: int,
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler


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

    for exc_type, status_code in _ERROR_STATUS.items():
        app.add_exception_handler(exc_type, _make_error_handler(status_code))

    app.include_router(artifacts.router)
    app.include_router(links.router)
    app.include_router(search.router)
    app.include_router(workflows.router)

    return app


app = create_app()
