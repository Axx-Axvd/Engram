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
- **LLM:** abstract provider — a deterministic **mock by default** (no tokens, offline); pluggable Anthropic/OpenAI
- **Orchestration:** a `WorkflowEngine` interface (procedural today; LangGraph-ready)

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

# 3. (optional) Seed a demo project — a small todo manager
uv run python ../../scripts/seed_demo.py --change

# 4. Frontend (separate terminal, from repo root)
pnpm install
pnpm web:dev                               # http://localhost:3000
```

Then open http://localhost:3000: **Formalize** a description into grouped documents, browse them
(each is a document of typed, numbered **items** with cross-references), inspect versions and links,
run a **Change request** to see impact + new versions, and view the **Consistency** report.

## What works today

- Documents grouped by type (Requirements / User stories / Tasks / Test cases) plus a Project brief,
  each holding structured **items** with cross-references — created by the formalize workflow or by hand.
- Versioning + change log on every edit; typed links between documents.
- Vector + graph **context retrieval** (`/api/search/context`).
- **Change-request** impact analysis: finds affected documents, writes new versions, links them.
- **Consistency** report: requirement coverage by tasks/tests, dangling references, etc.

The LLM is the deterministic mock, so generated text is templated; swapping in a real provider
changes only text quality, not the structure.

Out of MVP scope for now: authentication, UML/diagram generation, DOCX export, external
integrations (Jira/GitHub/Slack).
