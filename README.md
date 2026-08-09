# Engram

Engram is an evidence-backed change-impact analysis layer for long-lived software projects.
It indexes knowledge from existing sources, tracks the exact source revisions behind that
knowledge, finds requirements, decisions, code and tests affected by a proposed change, and builds
a small reproducible context package for an AI agent.

Engram is **not** a replacement for GitHub, an issue tracker, or a documentation editor. External
systems remain the source of truth. Engram's job is to connect and explain their information.

## Product loop

```text
fixed source revision
        ↓
versioned knowledge elements + typed evidence-backed links
        ↓
change request → impact analysis → human review
        ↓
bounded context package for an external agent
        ↓
actual commit / pull request → ChangeSet → consistency check
```

The current repository contains a functional prototype of the full non-mutating product loop. It
is not yet a validated MVP: the ten-change benchmark is prepared, but comparative results on a
real imported repository have not been recorded. See [`ENGRAM_TRUE_PATH_PLAN.md`](ENGRAM_TRUE_PATH_PLAN.md),
[`ROADMAP.md`](ROADMAP.md), and [`research/README.md`](research/README.md).

## What works

- FastAPI service with PostgreSQL, pgvector, SQLAlchemy and Alembic.
- Strict project isolation and immutable source provenance.
- Independently versioned knowledge items and reviewed, typed item links.
- Evidence-backed impact candidates with atomic structured-output validation and no automatic edits.
- Reproducible Context Packages with a hard post-expansion token budget.
- Read-only GitHub import at a fixed commit SHA, including Markdown, code, tests, issues, pull
  requests and causal ChangeSets.
- Deterministic mock LLM and embeddings for offline tests.
- Optional Claude Code provider for research runs.
- Project-oriented Next.js interface; the artifact editor and generic graph remain diagnostic tools.
- PostgreSQL-backed API tests, migration checks, frontend lint/build checks and GitHub Actions CI.

## Repository layout

```text
apps/api/      FastAPI application, domain model, migrations and tests
apps/web/      Next.js application and generated API client
infra/         PostgreSQL + pgvector development environment
docs/adr/      Architecture decisions
scripts/       Development and import utilities
```

## Local development

Requirements: Python 3.11+, Node.js 20+, pnpm 11, Docker and Docker Compose.

```bash
docker compose -f infra/docker-compose.yml up -d

cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn engram.main:app --reload

# another terminal, repository root
pnpm install
pnpm web:dev
```

The API is available at <http://localhost:8000> and the web application at
<http://localhost:3000>.

After reviewing impact candidates, build or retrieve the approved Context Package via the API or
the dependency-free CLI:

```bash
python scripts/engram_context.py --project <uuid> --analysis <uuid> --budget 4000
python scripts/engram_context.py --project <uuid> --package <uuid>
```

## Verification

The automated suite always uses the deterministic providers, regardless of a developer's `.env`.

```bash
cd apps/api
ENGRAM_LLM_PROVIDER=mock uv run pytest
uv run ruff check .

cd ../..
pnpm --filter @engram/web exec eslint .
pnpm --filter @engram/web exec next build
```

## Product boundary

Until the impact-analysis hypothesis is measured on a real repository, development is deliberately
focused on project isolation, provenance, item-level versioning, safe review, context delivery and
GitHub ingestion. Rich-text authoring, collaboration, extra integrations, auto-repair, Neo4j and
agent orchestration are frozen rather than expanded.
