"""Data access for artifacts, versions, and change logs."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from engram.enums import ArtifactStatus, ArtifactType
from engram.models import Artifact, ArtifactVersion, ChangeLog


def get(session: Session, artifact_id: uuid.UUID) -> Artifact | None:
    return session.get(Artifact, artifact_id)


def list_artifacts(
    session: Session,
    *,
    type_: ArtifactType | None = None,
    status: ArtifactStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Artifact]:
    stmt = select(Artifact)
    if type_ is not None:
        stmt = stmt.where(Artifact.type == type_)
    if status is not None:
        stmt = stmt.where(Artifact.status == status)
    stmt = stmt.order_by(Artifact.created_at).limit(limit).offset(offset)
    return list(session.scalars(stmt))


def add(session: Session, artifact: Artifact) -> Artifact:
    session.add(artifact)
    session.flush()
    return artifact


def delete(session: Session, artifact: Artifact) -> None:
    """Delete an artifact. DB-level ON DELETE CASCADE removes its versions,
    links (incoming and outgoing), and change logs."""
    session.delete(artifact)
    session.flush()


def add_version(session: Session, version: ArtifactVersion) -> ArtifactVersion:
    session.add(version)
    session.flush()
    return version


def list_versions(session: Session, artifact_id: uuid.UUID) -> list[ArtifactVersion]:
    stmt = (
        select(ArtifactVersion)
        .where(ArtifactVersion.artifact_id == artifact_id)
        .order_by(ArtifactVersion.version)
    )
    return list(session.scalars(stmt))


def get_active_version(session: Session, artifact_id: uuid.UUID) -> ArtifactVersion | None:
    stmt = select(ArtifactVersion).where(
        ArtifactVersion.artifact_id == artifact_id,
        ArtifactVersion.is_active.is_(True),
    )
    return session.scalars(stmt).first()


def add_changelog(session: Session, entry: ChangeLog) -> ChangeLog:
    session.add(entry)
    session.flush()
    return entry
