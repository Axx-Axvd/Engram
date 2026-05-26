# Engram — Agent Instructions

**Engram** is a project-memory platform for long AI projects. It stores project knowledge *outside*
the LLM as **connected, versioned artifacts** (Requirement, UserStory, Task, TestCase,
ChangeRequest), retrieves the **minimal relevant context** for each task instead of the whole
project, saves results back, and checks consistency across artifacts.

> The full approved plan (milestones M0–M6) lives at
> `C:\Users\PC\.claude\plans\cryptic-sniffing-russell.md`.

## Monorepo layout

```
apps/
  api/        FastAPI backend (Python, uv). Package: src/engram/. Env prefix: ENGRAM_.
  web/        Next.js (App Router) + TypeScript frontend (pnpm). Package: @engram/web.
packages/
  shared/     Shared TS types / contracts.
infra/
  docker-compose.yml   PostgreSQL 16 + pgvector (image pgvector/pgvector:pg16).
  initdb/              SQL run once on a fresh DB volume (enables the vector extension).
scripts/      Dev/seed scripts.
docs/
```

## Tech stack

- **Frontend:** Next.js + TypeScript, Tailwind CSS (+ shadcn/ui from M3), TanStack Query,
  React Flow (`@xyflow/react`, from M3) for the artifact graph.
- **Backend:** Python 3.11+ + FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2 / pydantic-settings.
- **Storage & search:** PostgreSQL 16 + pgvector (relational data + vector context retrieval).
- **LLM:** abstract `LLMProvider` with a deterministic `MockLLMProvider` by default
  (`ENGRAM_LLM_PROVIDER=mock`) — no token cost in dev. Pluggable Anthropic/OpenAI later.
- **Embeddings:** abstract adapter, local model default (`ENGRAM_EMBEDDING_PROVIDER=local`).
- **Orchestration:** LangGraph behind a `WorkflowEngine` interface (from M3).

## Common commands

Database (needs Docker Desktop running):
```bash
docker compose -f infra/docker-compose.yml up -d
```

Backend (from `apps/api/`):
```bash
uv sync                                   # create .venv + install deps
uv run alembic upgrade head               # apply migrations (needs the DB)
uv run uvicorn engram.main:app --reload   # http://localhost:8000  (docs at /docs)
uv run pytest                             # tests
uv run ruff check . && uv run ruff format .
```

Frontend (from repo root):
```bash
pnpm install
pnpm web:dev                              # http://localhost:3000
pnpm web:build
pnpm --filter @engram/web gen:api         # regen TS API types (backend must be running)
```

## Conventions & rules

- **Secrets:** never commit `.env`, `credentials.json`, `token.json`. Config is read from the
  repo-root `.env` with the `ENGRAM_` prefix (see `apps/api/src/engram/config.py`).
- **Mock by default:** LLM and embeddings default to mock/local so the full pipeline runs offline
  and tests stay deterministic. Don't call paid APIs without asking the user first.
- **API contract:** the frontend talks to the backend through a typed client generated from
  FastAPI's OpenAPI (`apps/web/src/lib/api/`). After changing backend endpoints/schemas, regenerate
  with `pnpm --filter @engram/web gen:api` (the generated `generated/` folder is gitignored).
- **Migrations:** every model change gets an Alembic migration
  (`uv run alembic revision --autogenerate -m "..."`), reviewed before `upgrade head`.
- **Layering (backend):** `api/` (routers) → `services/` (logic) → `repositories/` (data access)
  → `models/` (ORM). Keep LLM/embedding access behind their adapter interfaces.
- **Tests:** backend uses pytest; add tests with each milestone (workflows + validation rules).

## Domain model (reference)

- **Artifact** (head state) + **ArtifactVersion** (immutable snapshots, one marked active) +
  **ArtifactLink** (typed edges) + **ChangeLog**.
- **Artifact types:** requirement, user_story, task, test_case, change_request (decision_record
  later).
- **Link types:** refines, implements, tests, changes, depends_on, derived_from, related_to.
- **End-to-end scenario:** project description → requirements → user stories → tasks → test cases →
  change request → impact analysis → new versions + consistency report.

Out of MVP scope for now: auth, UML/diagram generation, DOCX export, external integrations
(Jira/GitHub/Slack), production-grade security.
