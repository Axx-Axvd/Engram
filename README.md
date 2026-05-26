# Engram

**Engram** is a project-memory platform for long AI projects. It stores project knowledge
*outside* the LLM as **connected, versioned artifacts** (requirements, user stories, tasks, test
cases, change requests), selects the **minimal relevant context** for each task instead of feeding
the whole project to the model, saves results back, and checks consistency across artifacts.

> *Engram* (neuroscience): a physical trace of memory. That's the idea — the durable memory of a
> project, living next to the model rather than inside it.

## Why

Long AI projects overflow the context window, lose old decisions, let artifacts drift out of sync,
make change-impact hard to reason about, and burn tokens re-reading everything. Engram is the
management layer that keeps project knowledge structured, linked, versioned, and retrievable.

## End-to-end scenario

```
project description → requirements → user stories → tasks → test cases
                    → change request → impact analysis → new versions + consistency report
```

## Monorepo layout

```
apps/
  api/        FastAPI backend — artifacts, versions, links, search, workflows (Python, uv)
  web/        Next.js + TypeScript frontend (pnpm)
packages/
  shared/     Shared TS types / generated API client
infra/
  docker-compose.yml   PostgreSQL 16 + pgvector
scripts/      Dev/seed scripts
docs/
```

## Tech stack

- **Frontend:** Next.js (App Router) + TypeScript, Tailwind CSS + shadcn/ui, TanStack Query, React Flow
- **Backend:** Python 3.11+ + FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2
- **Storage & search:** PostgreSQL 16 + pgvector (relational data + vector context retrieval)
- **LLM:** abstract provider with a deterministic mock first; pluggable Anthropic/OpenAI
- **Orchestration:** LangGraph behind a `WorkflowEngine` interface

## Quick start

```bash
# 0. Copy env
cp .env.example .env

# 1. Start the database
docker compose -f infra/docker-compose.yml up -d

# 2. Backend
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn engram.main:app --reload   # http://localhost:8000  (docs at /docs)

# 3. Frontend (separate terminal, from repo root)
pnpm install
pnpm web:dev                               # http://localhost:3000
```

## Status

Early MVP. See the milestone plan in `docs/` (and the working plan referenced there).
Out of MVP scope for now: authentication, UML/diagram generation, DOCX export, external
integrations (Jira/GitHub/Slack).
