"""MCP stdio server exposing Engram's context channel to an external agent.

Run it with the optional extra installed:

    uv sync --extra mcp
    uv run python -m engram.mcp.server

Register it with an agent that speaks MCP over stdio, for example in Claude Code:

    claude mcp add engram -- uv --directory apps/api run python -m engram.mcp.server

The tools are thin wrappers over `engram.mcp.operations`; all rules live in the services.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from typing import Any

from engram.db.base import SessionLocal
from engram.errors import EngramError
from engram.mcp import operations


def _run(call: Callable[..., Any], *, writes: bool) -> str:
    """Run one operation in its own session and return its JSON payload.

    A failed call rolls back, so a rejected model result or a pending review can never leave
    half-written state behind.
    """
    session = SessionLocal()
    try:
        result = call(session)
        if writes:
            session.commit()
        return json.dumps(result, ensure_ascii=False, indent=2)
    except EngramError as exc:
        session.rollback()
        return json.dumps({"error": type(exc).__name__, "detail": str(exc)}, ensure_ascii=False)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def build_server():  # pragma: no cover - requires the optional `mcp` extra
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("engram")

    @server.tool()
    def list_projects() -> str:
        """List Engram projects with their ids, so a name can be resolved to a project id."""
        return _run(operations.list_projects, writes=False)

    @server.tool()
    def analyze_change(
        project_id: str,
        query: str,
        budget: int = 4000,
        max_candidates: int = 20,
        retrieval_mode: str = "combined",
    ) -> str:
        """Find which requirements, decisions, code and tests a proposed change may affect.

        Returns evidence-backed candidates at pinned versions. Changes nothing: Engram never
        edits knowledge or writes back to the repository. A human reviews the candidates, and
        only approved ones can enter a context package.
        """
        return _run(
            lambda session: operations.analyze_change(
                session,
                project_id=uuid.UUID(project_id),
                query=query,
                budget=budget,
                max_candidates=max_candidates,
                retrieval_mode=retrieval_mode,
            ),
            writes=True,
        )

    @server.tool()
    def get_context(project_id: str, analysis_id: str, budget: int = 4000) -> str:
        """Get the bounded, reproducible context package of reviewed knowledge for an analysis.

        Each entry carries its exact version, source locator and the reason it was included.
        Fails while review is still pending — that is deliberate.
        """
        return _run(
            lambda session: operations.get_context(
                session,
                project_id=uuid.UUID(project_id),
                analysis_id=uuid.UUID(analysis_id),
                budget=budget,
            ),
            writes=True,
        )

    @server.tool()
    def list_context_packages(project_id: str) -> str:
        """List context packages already approved and built for a project, newest first."""
        return _run(
            lambda session: operations.list_context_packages(
                session, project_id=uuid.UUID(project_id)
            ),
            writes=False,
        )

    return server


def main() -> None:  # pragma: no cover - process entry point
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
