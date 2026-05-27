"""Context retrieval: pick the minimal relevant slice of project memory for a query.

Strategy: nearest artifacts by vector similarity (pgvector), with a keyword fallback when no
embeddings exist, then expand along the link graph for a few hops. Archived artifacts are skipped.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from engram.embeddings import get_embedding_provider
from engram.enums import ArtifactStatus
from engram.models import Artifact, ArtifactLink
from engram.schemas.search import ContextBundle, ContextQuery


def _vector_seeds(
    session: Session, query: str, limit: int, exclude_archived: bool
) -> list[Artifact]:
    qvec = get_embedding_provider().embed_one(query)
    stmt = select(Artifact).where(Artifact.embedding.isnot(None))
    if exclude_archived:
        stmt = stmt.where(Artifact.status != ArtifactStatus.archived)
    stmt = stmt.order_by(Artifact.embedding.cosine_distance(qvec)).limit(limit)
    return list(session.scalars(stmt))


def _keyword_seeds(
    session: Session, query: str, limit: int, exclude_archived: bool
) -> list[Artifact]:
    pattern = f"%{query}%"
    stmt = select(Artifact).where(
        or_(Artifact.title.ilike(pattern), Artifact.content.ilike(pattern))
    )
    if exclude_archived:
        stmt = stmt.where(Artifact.status != ArtifactStatus.archived)
    return list(session.scalars(stmt.limit(limit)))


def _links_touching(session: Session, ids: Iterable[uuid.UUID]) -> list[ArtifactLink]:
    id_list = list(ids)
    if not id_list:
        return []
    stmt = select(ArtifactLink).where(
        or_(ArtifactLink.source_id.in_(id_list), ArtifactLink.target_id.in_(id_list))
    )
    return list(session.scalars(stmt))


def _fetch_artifacts(
    session: Session, ids: Iterable[uuid.UUID], exclude_archived: bool
) -> list[Artifact]:
    id_list = list(ids)
    if not id_list:
        return []
    stmt = select(Artifact).where(Artifact.id.in_(id_list))
    if exclude_archived:
        stmt = stmt.where(Artifact.status != ArtifactStatus.archived)
    return list(session.scalars(stmt))


def select_context(session: Session, query: ContextQuery) -> ContextBundle:
    seeds = _vector_seeds(session, query.query, query.limit, query.exclude_archived)
    if not seeds:
        seeds = _keyword_seeds(session, query.query, query.limit, query.exclude_archived)

    selected: dict[uuid.UUID, Artifact] = {a.id: a for a in seeds}
    links: dict[uuid.UUID, ArtifactLink] = {}
    frontier: set[uuid.UUID] = set(selected)

    for _ in range(query.hops):
        if not frontier:
            break
        new_ids: set[uuid.UUID] = set()
        for link in _links_touching(session, frontier):
            links[link.id] = link
            for neighbor_id in (link.source_id, link.target_id):
                if neighbor_id not in selected:
                    new_ids.add(neighbor_id)
        neighbors = _fetch_artifacts(session, new_ids, query.exclude_archived)
        for artifact in neighbors:
            selected[artifact.id] = artifact
        frontier = {artifact.id for artifact in neighbors}

    # Keep only links whose both endpoints are in the selected set.
    bundle_links = [
        link for link in links.values() if link.source_id in selected and link.target_id in selected
    ]
    return ContextBundle(
        seed_ids=[seed.id for seed in seeds],
        artifacts=list(selected.values()),
        links=bundle_links,
    )
