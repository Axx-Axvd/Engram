"""FastAPI dependency that yields a database session per request."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from engram.db.base import SessionLocal


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
