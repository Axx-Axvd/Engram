"""Data access for artifact links."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from engram.enums import LinkType
from engram.models import ArtifactLink


def get(session: Session, link_id: uuid.UUID) -> ArtifactLink | None:
    return session.get(ArtifactLink, link_id)


def add(session: Session, link: ArtifactLink) -> ArtifactLink:
    session.add(link)
    session.flush()
    return link


def exists(session: Session, source_id: uuid.UUID, target_id: uuid.UUID, type_: LinkType) -> bool:
    stmt = select(ArtifactLink.id).where(
        ArtifactLink.source_id == source_id,
        ArtifactLink.target_id == target_id,
        ArtifactLink.type == type_,
    )
    return session.scalars(stmt).first() is not None


def list_for_artifact(session: Session, artifact_id: uuid.UUID) -> list[ArtifactLink]:
    """All links where the artifact is either source or target."""
    stmt = select(ArtifactLink).where(
        or_(ArtifactLink.source_id == artifact_id, ArtifactLink.target_id == artifact_id)
    )
    return list(session.scalars(stmt))


def list_all(session: Session, project_id: uuid.UUID | None = None) -> list[ArtifactLink]:
    stmt = select(ArtifactLink)
    if project_id is not None:
        stmt = stmt.where(ArtifactLink.project_id == project_id)
    return list(session.scalars(stmt))
