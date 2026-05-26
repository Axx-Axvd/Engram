# Engram API

FastAPI backend for Engram — the project-memory layer (artifacts, versions, links, context search,
workflows).

## Develop

```bash
uv sync                                   # create .venv and install deps (incl. dev group)
uv run alembic upgrade head               # apply migrations (needs Postgres running)
uv run uvicorn engram.main:app --reload   # http://localhost:8000 — docs at /docs
uv run pytest                             # tests
uv run ruff check .                       # lint
```

Configuration is read from the repo-root `.env` with the `ENGRAM_` prefix (see `engram/config.py`).
