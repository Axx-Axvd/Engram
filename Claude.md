# Engram — Agent Instructions

Engram is an evidence-backed change-impact and context-delivery layer for software projects. It
indexes fixed revisions of external sources, derives independently versioned knowledge items,
explains which items a proposed change may affect, requires human review, and emits a bounded
reproducible Context Package. External systems remain sources of truth; Engram does not apply
model suggestions or write back to GitHub.

The authoritative direction is `ENGRAM_TRUE_PATH_PLAN.md`. Read it together with `README.md`,
`ROADMAP.md`, `FROZEN_IDEAS.md`, and `docs/adr/ADR-001-product-boundary.md` before expanding scope.

## Monorepo layout

```text
apps/api/      FastAPI, SQLAlchemy, Alembic, domain services and tests
apps/web/      Next.js App Router, TypeScript and the generated OpenAPI client
infra/         PostgreSQL 16 + pgvector development environment
research/      labelled retrieval cases and experiment format
scripts/       seed, Context Package CLI and evaluation utilities
```

## Architecture

- PostgreSQL/pgvector is the only persistence and retrieval store.
- FastAPI routes call services, services call repositories, repositories access ORM models.
- `Project` is a hard isolation boundary. Project-owned queries must always include `project_id`.
- `SourceRevision` and `SourceLocator` are immutable provenance. New knowledge must resolve to a
  fixed revision and exact locator.
- `ArtifactItemRecord`/`ItemVersion` are canonical analysis units. Artifact JSON items are a
  compatibility representation only.
- Only confirmed item links may expand retrieval. Inferred links begin as proposed.
- Impact analysis is non-mutating. Invalid structured model output is rejected as one transaction.
- Context Packages pin exact versions and enforce their budget after graph expansion.
- `engram/mcp/` delivers packages to an external agent: `operations.py` holds protocol-independent
  calls over the existing services, `server.py` is a stdio adapter needing the `mcp` extra.
  Candidate review is never exposed to the agent.
- GitHub is read-only and is the only active integration.
- The mock LLM and embeddings are deterministic CI/default providers. Claude Code is optional for
  research runs.

## Common commands

```bash
docker compose -f infra/docker-compose.yml up -d

cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn engram.main:app --reload
uv run pytest
uv run ruff check .

cd ../..
pnpm --filter @engram/web gen:api   # API must be running
pnpm --filter @engram/web exec eslint .
pnpm --filter @engram/web exec next build
```

## Rules

- Never commit `.env` or credentials. GitHub tokens remain server-side and are never persisted in
  source configuration.
- Add an Alembic migration for every model change and test both existing-data and clean installs.
- Preserve the deterministic providers in tests regardless of a developer's local `.env`.
- Regenerate the frontend OpenAPI types after backend contract changes; generated files are ignored.
- Keep rich-text editing and the generic graph as diagnostic compatibility surfaces.
- Auth/roles, collaboration, additional integrations, auto-repair, Neo4j, LangGraph and visual
  polish are frozen until the retrieval experiment validates the core loop.
