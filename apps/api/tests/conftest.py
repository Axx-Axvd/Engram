"""Pytest fixtures: an isolated Postgres test database with per-test truncation."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

# Tests are deterministic regardless of a developer's local .env.
os.environ["ENGRAM_LLM_PROVIDER"] = "mock"
os.environ["ENGRAM_EMBEDDING_PROVIDER"] = "mock"

import engram.models  # noqa: E402, F401  -- register models on Base.metadata
from engram.config import settings
from engram.db.base import Base
from engram.db.session import get_session
from engram.main import app

TEST_DB_NAME = "engram_test"
_TABLES = "projects"


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    base_url = make_url(settings.db_url)

    # Create the test database (CREATE DATABASE cannot run inside a transaction).
    admin = create_engine(base_url.set(database="engram"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB_NAME}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()

    test_engine = create_engine(base_url.set(database=TEST_DB_NAME))
    with test_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)

    yield test_engine
    test_engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    session = Session(bind=engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine: Engine) -> Generator[TestClient, None, None]:
    test_sessionmaker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_session() -> Generator[Session, None, None]:
        session = test_sessionmaker()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
