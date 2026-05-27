"""Artifact lifecycle logic: creation, versioning, and status changes.

An artifact is a *document* with a free-text ``content`` overview and a list of structured
``items``. Every mutation creates an immutable ``ArtifactVersion`` snapshot (exactly one active)
and appends a ``ChangeLog`` entry. Callers are responsible for committing the session.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from engram.embeddings import get_embedding_provider
from engram.enums import ArtifactStatus, ChangeAction
from engram.errors import NotFoundError
from engram.models import Artifact, ArtifactVersion, ChangeLog
from engram.repositories import artifact_repo
from engram.schemas.artifact import ArtifactCreate, ArtifactItem, ArtifactUpdate


def _items_to_json(items: list[ArtifactItem]) -> list[dict]:
    return [item.model_dump(mode="json") for item in items]


def _embed(title: str, content: str, items_json: list[dict]) -> list[float]:
    parts = [title, content]
    for item in items_json:
        parts.append(str(item.get("title", "")))
        parts.append(str(item.get("text", "")))
    text = "\n".join(part for part in parts if part)
    return get_embedding_provider().embed_one(text)


def create_artifact(session: Session, data: ArtifactCreate) -> Artifact:
    status = data.status or ArtifactStatus.draft
    items_json = _items_to_json(data.items)
    artifact = Artifact(
        type=data.type,
        title=data.title,
        content=data.content,
        items=items_json,
        status=status,
        current_version=1,
        source_ref=data.source_ref,
        embedding=_embed(data.title, data.content, items_json),
        created_by=data.created_by,
        updated_by=data.created_by,
    )
    artifact_repo.add(session, artifact)

    artifact_repo.add_version(
        session,
        ArtifactVersion(
            artifact_id=artifact.id,
            version=1,
            title=artifact.title,
            content=artifact.content,
            items=items_json,
            status=artifact.status,
            reason="created",
            is_active=True,
            created_by=data.created_by,
        ),
    )
    artifact_repo.add_changelog(
        session,
        ChangeLog(
            artifact_id=artifact.id,
            action=ChangeAction.created,
            detail=f"{artifact.type.value} created",
            created_by=data.created_by,
        ),
    )
    return artifact


def get_artifact(session: Session, artifact_id: uuid.UUID) -> Artifact:
    artifact = artifact_repo.get(session, artifact_id)
    if artifact is None:
        raise NotFoundError(f"Artifact {artifact_id} not found")
    return artifact


def update_artifact(session: Session, artifact_id: uuid.UUID, data: ArtifactUpdate) -> Artifact:
    """Apply a partial update. Any real change produces a new active version."""
    artifact = get_artifact(session, artifact_id)

    changed = False
    status_changed = False
    text_changed = False
    if data.title is not None and data.title != artifact.title:
        artifact.title = data.title
        changed = True
        text_changed = True
    if data.content is not None and data.content != artifact.content:
        artifact.content = data.content
        changed = True
        text_changed = True
    if data.items is not None:
        new_items = _items_to_json(data.items)
        if new_items != artifact.items:
            artifact.items = new_items
            changed = True
            text_changed = True
    if data.source_ref is not None and data.source_ref != artifact.source_ref:
        artifact.source_ref = data.source_ref
        changed = True
    if data.status is not None and data.status != artifact.status:
        artifact.status = data.status
        changed = True
        status_changed = True

    if not changed:
        return artifact

    if text_changed:
        artifact.embedding = _embed(artifact.title, artifact.content, artifact.items)

    previous = artifact_repo.get_active_version(session, artifact.id)
    if previous is not None:
        previous.is_active = False

    artifact.current_version += 1
    artifact.updated_by = data.updated_by

    artifact_repo.add_version(
        session,
        ArtifactVersion(
            artifact_id=artifact.id,
            version=artifact.current_version,
            title=artifact.title,
            content=artifact.content,
            items=artifact.items,
            status=artifact.status,
            reason=data.reason,
            is_active=True,
            created_by=data.updated_by,
        ),
    )
    artifact_repo.add_changelog(
        session,
        ChangeLog(
            artifact_id=artifact.id,
            action=ChangeAction.version_created,
            detail=f"v{artifact.current_version}",
            reason=data.reason,
            created_by=data.updated_by,
        ),
    )
    if status_changed:
        artifact_repo.add_changelog(
            session,
            ChangeLog(
                artifact_id=artifact.id,
                action=ChangeAction.status_changed,
                detail=f"-> {artifact.status.value}",
                created_by=data.updated_by,
            ),
        )
    return artifact


def list_versions(session: Session, artifact_id: uuid.UUID) -> list[ArtifactVersion]:
    # Ensure the artifact exists so callers get a clean 404 rather than an empty list.
    get_artifact(session, artifact_id)
    return artifact_repo.list_versions(session, artifact_id)
