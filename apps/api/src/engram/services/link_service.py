"""Artifact link logic: validated creation of typed edges between artifacts."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from engram.enums import ChangeAction
from engram.errors import ConflictError, NotFoundError, ValidationError
from engram.models import ArtifactLink, ChangeLog
from engram.repositories import artifact_repo, link_repo
from engram.schemas.link import LinkCreate


def create_link(session: Session, data: LinkCreate) -> ArtifactLink:
    if data.source_id == data.target_id:
        raise ValidationError("A link cannot connect an artifact to itself")

    if artifact_repo.get(session, data.source_id) is None:
        raise NotFoundError(f"Source artifact {data.source_id} not found")
    if artifact_repo.get(session, data.target_id) is None:
        raise NotFoundError(f"Target artifact {data.target_id} not found")

    if link_repo.exists(session, data.source_id, data.target_id, data.type):
        raise ConflictError("An identical link already exists")

    link = ArtifactLink(
        source_id=data.source_id,
        target_id=data.target_id,
        type=data.type,
        created_by=data.created_by,
    )
    link_repo.add(session, link)
    artifact_repo.add_changelog(
        session,
        ChangeLog(
            artifact_id=data.source_id,
            action=ChangeAction.linked,
            detail=f"{data.type.value} -> {data.target_id}",
            created_by=data.created_by,
        ),
    )
    return link


def list_links_for_artifact(session: Session, artifact_id: uuid.UUID) -> list[ArtifactLink]:
    if artifact_repo.get(session, artifact_id) is None:
        raise NotFoundError(f"Artifact {artifact_id} not found")
    return link_repo.list_for_artifact(session, artifact_id)
