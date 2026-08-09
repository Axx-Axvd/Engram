"""Project-scoped, explainable and budgeted context retrieval."""

from __future__ import annotations

import math
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from engram.embeddings import get_embedding_provider
from engram.enums import ArtifactStatus, LinkState, LinkType
from engram.models import (
    Artifact,
    ArtifactItemRecord,
    ArtifactLink,
    ItemVersion,
    SourceLocator,
)
from engram.repositories import item_repo
from engram.schemas.search import ContextBundle, ContextQuery
from engram.services import project_service

_TERM = re.compile(r"[\w.-]+", re.UNICODE)
_GRAPH_WEIGHT: dict[LinkType, float] = {
    LinkType.changes: 0.95,
    LinkType.implements: 0.9,
    LinkType.tests: 0.88,
    LinkType.refines: 0.85,
    LinkType.depends_on: 0.8,
    LinkType.derived_from: 0.7,
    LinkType.related_to: 0.55,
}


@dataclass(frozen=True)
class SelectedElement:
    item: ArtifactItemRecord
    version: ItemVersion
    locator: SourceLocator | None
    score: float
    reason: dict
    graph_path: list[dict]
    token_estimate: int


def estimate_tokens(title: str, text: str) -> int:
    # Stable, provider-independent estimate that deliberately rounds up.
    return max(1, math.ceil((len(title) + len(text) + 1) / 4))


def _vector_seeds(
    session: Session,
    project_id: uuid.UUID,
    query: str,
    limit: int,
    exclude_archived: bool,
) -> list[Artifact]:
    qvec = get_embedding_provider().embed_one(query)
    stmt = select(Artifact).where(
        Artifact.project_id == project_id,
        Artifact.embedding.isnot(None),
    )
    if exclude_archived:
        stmt = stmt.where(Artifact.status != ArtifactStatus.archived)
    stmt = stmt.order_by(Artifact.embedding.cosine_distance(qvec)).limit(limit)
    return list(session.scalars(stmt))


def _keyword_seeds(
    session: Session,
    project_id: uuid.UUID,
    query: str,
    limit: int,
    exclude_archived: bool,
) -> list[Artifact]:
    pattern = f"%{query}%"
    stmt = select(Artifact).where(
        Artifact.project_id == project_id,
        or_(Artifact.title.ilike(pattern), Artifact.content.ilike(pattern)),
    )
    if exclude_archived:
        stmt = stmt.where(Artifact.status != ArtifactStatus.archived)
    return list(session.scalars(stmt.limit(limit)))


def _links_touching(
    session: Session, project_id: uuid.UUID, ids: Iterable[uuid.UUID]
) -> list[ArtifactLink]:
    id_list = list(ids)
    if not id_list:
        return []
    stmt = select(ArtifactLink).where(
        ArtifactLink.project_id == project_id,
        or_(ArtifactLink.source_id.in_(id_list), ArtifactLink.target_id.in_(id_list)),
    )
    return list(session.scalars(stmt))


def _fetch_artifacts(
    session: Session,
    project_id: uuid.UUID,
    ids: Iterable[uuid.UUID],
    exclude_archived: bool,
) -> list[Artifact]:
    id_list = list(ids)
    if not id_list:
        return []
    stmt = select(Artifact).where(
        Artifact.project_id == project_id,
        Artifact.id.in_(id_list),
    )
    if exclude_archived:
        stmt = stmt.where(Artifact.status != ArtifactStatus.archived)
    return list(session.scalars(stmt))


def select_context(session: Session, query: ContextQuery) -> ContextBundle:
    """Legacy document bundle, now strictly limited to one project."""
    project_id = project_service.resolve_project_id(session, query.project_id)
    seeds = _vector_seeds(session, project_id, query.query, query.limit, query.exclude_archived)
    if not seeds:
        seeds = _keyword_seeds(
            session, project_id, query.query, query.limit, query.exclude_archived
        )

    selected: dict[uuid.UUID, Artifact] = {artifact.id: artifact for artifact in seeds}
    links: dict[uuid.UUID, ArtifactLink] = {}
    frontier: set[uuid.UUID] = set(selected)

    for _ in range(query.hops):
        if not frontier:
            break
        new_ids: set[uuid.UUID] = set()
        for link in _links_touching(session, project_id, frontier):
            links[link.id] = link
            for neighbor_id in (link.source_id, link.target_id):
                if neighbor_id not in selected:
                    new_ids.add(neighbor_id)
        neighbors = _fetch_artifacts(session, project_id, new_ids, query.exclude_archived)
        for artifact in neighbors:
            selected[artifact.id] = artifact
        frontier = {artifact.id for artifact in neighbors}

    bundle_links = [
        link for link in links.values() if link.source_id in selected and link.target_id in selected
    ]
    return ContextBundle(
        seed_ids=[seed.id for seed in seeds],
        artifacts=list(selected.values()),
        links=bundle_links,
    )


def _terms(text: str) -> set[str]:
    return {term.lower() for term in _TERM.findall(text) if len(term) >= 2}


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return float(max(-1.0, min(1.0, numerator / (left_norm * right_norm))))


def select_context_elements(
    session: Session,
    *,
    project_id: uuid.UUID,
    query: str,
    limit: int = 20,
    hops: int = 2,
    token_budget: int = 4000,
    retrieval_mode: str = "combined",
) -> list[SelectedElement]:
    """Return exact item versions with explanations under a hard post-expansion budget."""
    project_service.get_project(session, project_id)
    query_terms = _terms(query)
    query_vector = get_embedding_provider().embed_one(query)
    all_items = item_repo.list_items(session, project_id)
    if retrieval_mode not in {"full", "vector", "graph", "combined"}:
        raise ValueError(f"Unknown retrieval mode: {retrieval_mode}")

    scored: dict[uuid.UUID, tuple[float, dict, list[dict]]] = {}
    for item in all_items:
        text_terms = _terms(f"{item.key} {item.title} {item.text}")
        matches = sorted(query_terms & text_terms)
        lexical = len(matches) / max(1, len(query_terms))
        vector = _cosine(list(item.embedding), query_vector) if item.embedding is not None else 0
        explicit = 1.0 if item.key.lower() in query.lower() else 0.0
        if retrieval_mode == "full":
            score = 1.0
        elif retrieval_mode == "vector":
            score = max(0.0, vector)
        elif retrieval_mode == "graph":
            score = 0.85 * lexical + 0.15 * explicit
        else:
            score = 0.45 * max(0.0, vector) + 0.4 * lexical + 0.15 * explicit
        if score <= 0 and query_terms:
            continue
        scored[item.id] = (
            score,
            {
                "stage": "retrieval",
                "matched_terms": matches,
                "lexical_score": round(lexical, 6),
                "vector_score": round(vector, 6),
                "explicit_key": bool(explicit),
                "retrieval_mode": retrieval_mode,
            },
            [],
        )

    seed_ids = (
        set(scored)
        if retrieval_mode == "full"
        else {
            item_id
            for item_id, _ in sorted(scored.items(), key=lambda pair: pair[1][0], reverse=True)[
                :limit
            ]
        }
    )
    selected_ids = set(seed_ids)
    frontier = set(seed_ids)
    graph_hops = hops if retrieval_mode in {"graph", "combined"} else 0
    for _depth in range(graph_hops):
        if not frontier:
            break
        next_frontier: set[uuid.UUID] = set()
        for link in item_repo.links_touching(session, project_id, frontier):
            if link.state != LinkState.confirmed.value:
                continue
            endpoints = (link.source_item_id, link.target_item_id)
            for origin_id in frontier & set(endpoints):
                neighbor_id = endpoints[1] if endpoints[0] == origin_id else endpoints[0]
                if neighbor_id in selected_ids:
                    continue
                neighbor = item_repo.get(session, neighbor_id, project_id)
                if neighbor is None or neighbor.valid_to is not None:
                    continue
                parent_score, _, parent_path = scored.get(origin_id, (0.1, {"stage": "graph"}, []))
                graph_score = parent_score * _GRAPH_WEIGHT.get(link.type, 0.5)
                scored[neighbor_id] = (
                    graph_score,
                    {
                        "stage": "graph_expansion",
                        "from_item_id": str(origin_id),
                        "link_id": str(link.id),
                        "link_type": link.type.value,
                        "link_origin": link.origin,
                    },
                    [
                        *parent_path,
                        {
                            "link_id": str(link.id),
                            "type": link.type.value,
                            "from": str(origin_id),
                            "to": str(neighbor_id),
                        },
                    ],
                )
                selected_ids.add(neighbor_id)
                next_frontier.add(neighbor_id)
        frontier = next_frontier

    ranked: list[SelectedElement] = []
    used_tokens = 0
    for item_id, (score, reason, graph_path) in sorted(
        ((item_id, scored[item_id]) for item_id in selected_ids),
        key=lambda pair: pair[1][0],
        reverse=True,
    ):
        item = item_repo.get(session, item_id, project_id)
        if item is None:
            continue
        version = item_repo.current_version(session, item)
        if version is None or not version.is_active:
            continue
        tokens = estimate_tokens(version.title, version.text)
        if used_tokens + tokens > token_budget:
            continue
        locator = (
            session.get(SourceLocator, version.source_locator_id)
            if version.source_locator_id is not None
            else None
        )
        ranked.append(
            SelectedElement(
                item=item,
                version=version,
                locator=locator,
                score=round(score, 6),
                reason=reason,
                graph_path=graph_path,
                token_estimate=tokens,
            )
        )
        used_tokens += tokens
    return ranked
