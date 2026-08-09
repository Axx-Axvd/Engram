"""Artifact lifecycle logic: creation, versioning, and status changes.

An artifact is a *document* with a free-text ``content`` overview and a list of structured
``items``. Every mutation creates an immutable ``ArtifactVersion`` snapshot (exactly one active)
and appends a ``ChangeLog`` entry. Callers are responsible for committing the session.
"""

from __future__ import annotations

import json
import re
import uuid

from sqlalchemy.orm import Session

from engram.embeddings import get_embedding_provider
from engram.enums import ArtifactStatus, ChangeAction, status_allowed_for_type
from engram.errors import NotFoundError, ValidationError
from engram.models import Artifact, ArtifactVersion, ChangeLog
from engram.repositories import artifact_repo
from engram.schemas.artifact import ArtifactCreate, ArtifactItem, ArtifactUpdate
from engram.services import item_service, project_service, provenance_service


def _items_to_json(items: list[ArtifactItem]) -> list[dict]:
    return [item.model_dump(mode="json") for item in items]


def content_to_text(content: str) -> str:
    """Plain text from a document body.

    The body is rich-text stored as serialized Tiptap JSON; legacy/seed bodies and
    change-request output are raw text. We extract just the words so embeddings index the
    prose, not JSON syntax. Non-JSON (or non-Tiptap) input is returned unchanged.
    """
    stripped = content.strip() if content else ""
    if not stripped:
        return ""
    try:
        doc = json.loads(stripped)
    except (ValueError, TypeError):
        return content
    if not isinstance(doc, dict) or doc.get("type") != "doc":
        return content

    parts: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("text"), str):
                parts.append(node["text"])
            attrs = node.get("attrs")
            if isinstance(attrs, dict) and isinstance(attrs.get("summary"), str):
                parts.append(attrs["summary"])
            walk(node.get("content"))
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(doc)
    return " ".join(part for part in parts if part)


def text_to_doc(text: str) -> str:
    """Serialize plain text into a minimal Tiptap document (JSON string).

    Inverse of :func:`content_to_text`. Mirrors the frontend ``plainTextToDoc``: blank lines
    separate paragraphs, single newlines become hard breaks. Used to wrap plain-text LLM output
    so the stored ``content`` is always valid Tiptap JSON.
    """
    paragraphs = re.split(r"\n{2,}", text.replace("\r\n", "\n"))
    content: list[dict] = []
    for para in paragraphs:
        lines = para.split("\n")
        inline: list[dict] = []
        for i, line in enumerate(lines):
            if i > 0:
                inline.append({"type": "hardBreak"})
            if line:
                inline.append({"type": "text", "text": line})
        content.append(
            {"type": "paragraph", "content": inline} if inline else {"type": "paragraph"}
        )
    return json.dumps({"type": "doc", "content": content})


def _embed(title: str, content: str, items_json: list[dict]) -> list[float]:
    parts = [title, content_to_text(content)]
    for item in items_json:
        parts.append(str(item.get("title", "")))
        parts.append(str(item.get("text", "")))
    text = "\n".join(part for part in parts if part)
    return get_embedding_provider().embed_one(text)


def create_artifact(session: Session, data: ArtifactCreate) -> Artifact:
    project_id = project_service.resolve_project_id(session, data.project_id)
    status = data.status or (
        ArtifactStatus.proposed if data.type.value == "change_request" else ArtifactStatus.draft
    )
    items_json = _items_to_json(data.items)
    if data.source_locator_id is not None:
        locator = provenance_service.require_locator(session, project_id, data.source_locator_id)
    else:
        locator = provenance_service.ensure_manual_locator(
            session,
            project_id,
            label=data.title,
            content=f"{data.title}\n{content_to_text(data.content)}",
            source_ref=data.source_ref,
            created_by=data.created_by,
        )
    artifact = Artifact(
        project_id=project_id,
        type=data.type,
        title=data.title,
        content=data.content,
        items=items_json,
        status=status,
        current_version=1,
        source_ref=data.source_ref,
        source_locator_id=locator.id,
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
            project_id=project_id,
            artifact_id=artifact.id,
            action=ChangeAction.created,
            detail=f"{artifact.type.value} created",
            created_by=data.created_by,
        ),
    )
    item_service.sync_artifact_items(
        session,
        artifact,
        reason="artifact created",
        created_by=data.created_by,
    )
    return artifact


def get_artifact(
    session: Session, artifact_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> Artifact:
    artifact = artifact_repo.get(session, artifact_id, project_id)
    if artifact is None:
        raise NotFoundError(f"Artifact {artifact_id} not found")
    return artifact


def delete_artifact(
    session: Session, artifact_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> None:
    """Remove an artifact and everything that hangs off it (versions, links, change logs)."""
    artifact = get_artifact(session, artifact_id, project_id)
    artifact_repo.delete(session, artifact)


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
    if data.source_locator_id is not None and data.source_locator_id != artifact.source_locator_id:
        provenance_service.require_locator(session, artifact.project_id, data.source_locator_id)
        artifact.source_locator_id = data.source_locator_id
        changed = True
        text_changed = True
    if data.status is not None and data.status != artifact.status:
        if not status_allowed_for_type(artifact.type, data.status):
            raise ValidationError(
                f"status '{data.status.value}' is not valid for type '{artifact.type.value}'"
            )
        artifact.status = data.status
        changed = True
        status_changed = True

    if not changed:
        return artifact

    if text_changed:
        if data.source_locator_id is None:
            locator = provenance_service.ensure_manual_locator(
                session,
                artifact.project_id,
                label=artifact.title,
                content=f"{artifact.title}\n{content_to_text(artifact.content)}",
                source_ref=artifact.source_ref,
                created_by=data.updated_by,
            )
            artifact.source_locator_id = locator.id
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
            project_id=artifact.project_id,
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
                project_id=artifact.project_id,
                artifact_id=artifact.id,
                action=ChangeAction.status_changed,
                detail=f"-> {artifact.status.value}",
                created_by=data.updated_by,
            ),
        )
    if text_changed:
        item_service.sync_artifact_items(
            session,
            artifact,
            reason=data.reason or "artifact updated",
            created_by=data.updated_by,
        )
    return artifact


def list_versions(session: Session, artifact_id: uuid.UUID) -> list[ArtifactVersion]:
    # Ensure the artifact exists so callers get a clean 404 rather than an empty list.
    get_artifact(session, artifact_id)
    return artifact_repo.list_versions(session, artifact_id)
