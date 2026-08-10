"""Protocol-independent operations behind the MCP channel.

Every call reuses the existing services, so the agent-facing channel cannot drift from the
product rules: analysis never mutates knowledge, a package only ever contains reviewed
candidates at pinned versions, and the token budget is enforced after graph expansion.

Deliberately absent: reviewing candidates. Approving an impact candidate is the human decision
the whole loop is built around, so it stays outside the agent's reach.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from engram.enums import RetrievalMode
from engram.repositories import project_repo
from engram.schemas.analysis import ContextPackageRead, ImpactAnalysisCreate, ImpactAnalysisRead
from engram.services import analysis_service

_REVIEW_HINT = (
    "Engram does not apply anything on its own. A human reviews these candidates, and only "
    "approved ones can enter a context package."
)


def list_projects(session: Session) -> list[dict]:
    """Every project an agent may analyse, so it can resolve a name to an id. Reads only."""
    return [
        {"project_id": str(project.id), "name": project.name, "slug": project.slug}
        for project in project_repo.list_projects(session)
    ]


def _candidate_payload(analysis: ImpactAnalysisRead) -> list[dict]:
    return [
        {
            "candidate_id": str(candidate.id),
            "item_id": str(candidate.item_id),
            "item_version_id": str(candidate.item_version_id),
            "impact": candidate.impact_type,
            "confidence": candidate.confidence,
            "why": candidate.rationale,
            "evidence": candidate.evidence,
            "selection_reason": candidate.selection_reason,
            "proposed_action": candidate.proposed_action,
            "review_decision": candidate.decision,
        }
        for candidate in analysis.candidates
    ]


def analyze_change(
    session: Session,
    *,
    project_id: uuid.UUID,
    query: str,
    budget: int = 4000,
    max_candidates: int = 20,
    retrieval_mode: str = RetrievalMode.combined.value,
    created_by: str = "mcp",
) -> dict:
    """Find the knowledge a proposed change may affect. Changes nothing."""
    analysis = analysis_service.create_analysis(
        session,
        project_id,
        ImpactAnalysisCreate(
            query=query,
            context_budget=budget,
            max_candidates=max_candidates,
            retrieval_mode=RetrievalMode(retrieval_mode),
            created_by=created_by,
        ),
    )
    return {
        "analysis_id": str(analysis.id),
        "project_id": str(analysis.project_id),
        "summary": analysis.summary,
        "status": analysis.status,
        "retrieval_mode": analysis.retrieval_mode,
        "algorithm_version": analysis.algorithm_version,
        "context_budget": analysis.context_budget,
        "candidates": _candidate_payload(analysis),
        "next_step": _REVIEW_HINT,
    }


def _package_payload(package: ContextPackageRead) -> dict:
    return {
        "package_id": str(package.id),
        "project_id": str(package.project_id),
        "analysis_id": str(package.analysis_id),
        "token_budget": package.token_budget,
        "token_estimate": package.token_estimate,
        "created_at": package.created_at.isoformat(),
        "items": [
            {
                "rank": entry.rank,
                "score": entry.score,
                "token_estimate": entry.token_estimate,
                "type": entry.item.type,
                "key": entry.item.key,
                "title": entry.version.title,
                "text": entry.version.text,
                "item_version": entry.version.version,
                "item_version_id": str(entry.version.id),
                "source": (
                    None
                    if entry.source_locator is None
                    else {
                        "path": entry.source_locator.path,
                        "start_line": entry.source_locator.start_line,
                        "end_line": entry.source_locator.end_line,
                        "url": entry.source_locator.url,
                        "content_hash": entry.source_locator.content_hash,
                    }
                ),
                "reason": entry.reason,
                "graph_path": entry.graph_path,
            }
            for entry in package.items
        ],
    }


def get_context(
    session: Session,
    *,
    project_id: uuid.UUID,
    analysis_id: uuid.UUID,
    budget: int = 4000,
    created_by: str = "mcp",
) -> dict:
    """Build the bounded, reproducible package of reviewed knowledge for an analysis.

    Fails while review is pending: an unreviewed candidate must not reach an agent as fact.
    """
    package = analysis_service.build_context_package(
        session,
        project_id,
        analysis_id,
        token_budget=budget,
        created_by=created_by,
    )
    return _package_payload(package)


def list_context_packages(session: Session, *, project_id: uuid.UUID) -> list[dict]:
    """Packages already approved and built, newest first, without rebuilding one."""
    return [
        {
            "package_id": str(package.id),
            "analysis_id": str(package.analysis_id),
            "token_budget": package.token_budget,
            "token_estimate": package.token_estimate,
            "items": len(package.items),
            "created_at": package.created_at.isoformat(),
        }
        for package in analysis_service.list_context_packages(session, project_id)
    ]
