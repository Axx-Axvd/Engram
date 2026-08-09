"""Artifact link logic: validated creation of typed edges between artifacts."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from engram.enums import ArtifactType, ChangeAction, LinkType
from engram.errors import ConflictError, NotFoundError, ValidationError
from engram.models import ArtifactLink, ChangeLog
from engram.repositories import artifact_repo, link_repo
from engram.schemas.link import LinkCreate


def create_link(session: Session, data: LinkCreate) -> ArtifactLink:
    if data.source_id == data.target_id:
        raise ValidationError("A link cannot connect an artifact to itself")

    source = artifact_repo.get(session, data.source_id)
    if source is None:
        raise NotFoundError(f"Source artifact {data.source_id} not found")
    target = artifact_repo.get(session, data.target_id)
    if target is None:
        raise NotFoundError(f"Target artifact {data.target_id} not found")
    if source.project_id != target.project_id:
        raise ValidationError("A link cannot cross project boundaries")
    if data.project_id is not None and data.project_id != source.project_id:
        raise ValidationError("Link project does not match its artifacts")

    allowed = {
        LinkType.refines: {(ArtifactType.user_story, ArtifactType.requirement)},
        LinkType.implements: {(ArtifactType.task, ArtifactType.requirement)},
        LinkType.tests: {(ArtifactType.test_case, ArtifactType.requirement)},
        LinkType.changes: {
            (ArtifactType.change_request, ArtifactType.requirement),
            (ArtifactType.change_request, ArtifactType.user_story),
            (ArtifactType.change_request, ArtifactType.task),
            (ArtifactType.change_request, ArtifactType.test_case),
        },
    }
    if data.type in allowed and (source.type, target.type) not in allowed[data.type]:
        raise ValidationError(
            f"Link '{data.type.value}' is not valid from '{source.type.value}' "
            f"to '{target.type.value}'"
        )

    if link_repo.exists(session, data.source_id, data.target_id, data.type):
        raise ConflictError("An identical link already exists")

    link = ArtifactLink(
        project_id=source.project_id,
        source_id=data.source_id,
        target_id=data.target_id,
        type=data.type,
        created_by=data.created_by,
    )
    link_repo.add(session, link)
    artifact_repo.add_changelog(
        session,
        ChangeLog(
            project_id=source.project_id,
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
