"""Canonical knowledge-item versioning and evidence-aware typed links."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from engram.embeddings import get_embedding_provider
from engram.enums import ArtifactType, ItemType, LinkOrigin, LinkState, LinkType
from engram.errors import ConflictError, NotFoundError, ValidationError
from engram.models import Artifact, ArtifactItemRecord, EvidenceRef, ItemLink, ItemVersion
from engram.repositories import artifact_repo, item_repo, source_repo
from engram.schemas.item import ItemCreate, ItemLinkCreate, ItemLinkReview, ItemUpdate
from engram.services import project_service, provenance_service

_ARTIFACT_ITEM_TYPE: dict[ArtifactType, ItemType] = {
    ArtifactType.project_brief: ItemType.document,
    ArtifactType.requirement: ItemType.requirement,
    ArtifactType.user_story: ItemType.user_story,
    ArtifactType.task: ItemType.task,
    ArtifactType.test_case: ItemType.test,
    ArtifactType.change_request: ItemType.change_request,
}

_ALLOWED_LINKS: dict[LinkType, set[tuple[str, str]]] = {
    LinkType.refines: {
        (ItemType.user_story.value, ItemType.requirement.value),
        (ItemType.requirement.value, ItemType.requirement.value),
        (ItemType.decision.value, ItemType.requirement.value),
    },
    LinkType.implements: {
        (ItemType.task.value, ItemType.requirement.value),
        (ItemType.task.value, ItemType.decision.value),
        (ItemType.code_component.value, ItemType.requirement.value),
        (ItemType.code_component.value, ItemType.decision.value),
    },
    LinkType.tests: {
        (ItemType.test.value, ItemType.requirement.value),
        (ItemType.test.value, ItemType.code_component.value),
        (ItemType.test.value, ItemType.task.value),
    },
}


def _embedding(title: str, text: str) -> list[float]:
    return get_embedding_provider().embed_one(f"{title}\n{text}".strip())


def _source_revision_id(session: Session, locator_id: uuid.UUID | None) -> uuid.UUID | None:
    if locator_id is None:
        return None
    locator = source_repo.get_locator(session, locator_id)
    return locator.source_revision_id if locator is not None else None


def _new_version(
    session: Session,
    item: ArtifactItemRecord,
    *,
    reason: str,
    created_by: str,
) -> ItemVersion:
    previous = item_repo.current_version(session, item)
    version_number = 1
    if previous is not None:
        previous.is_active = False
        version_number = previous.version + 1
    version = item_repo.add(
        session,
        ItemVersion(
            item_id=item.id,
            version=version_number,
            title=item.title,
            text=item.text,
            status=item.status,
            source_revision_id=_source_revision_id(session, item.source_locator_id),
            source_locator_id=item.source_locator_id,
            reason=reason,
            is_active=True,
            created_by=created_by,
        ),
    )
    item.current_version_id = version.id
    session.flush()
    return version


def create_item(session: Session, project_id: uuid.UUID, data: ItemCreate) -> ArtifactItemRecord:
    project_service.get_project(session, project_id)
    provenance_service.require_locator(session, project_id, data.source_locator_id)
    if (
        data.artifact_id is not None
        and artifact_repo.get(session, data.artifact_id, project_id) is None
    ):
        raise ValidationError("Artifact does not belong to the selected project")
    if data.artifact_id and item_repo.get_by_artifact_key(session, data.artifact_id, data.key):
        raise ConflictError(f"Item key '{data.key}' already exists in the artifact")
    item = item_repo.add(
        session,
        ArtifactItemRecord(
            project_id=project_id,
            artifact_id=data.artifact_id,
            key=data.key,
            type=data.type.value,
            title=data.title,
            text=data.text,
            status=data.status,
            source_locator_id=data.source_locator_id,
            embedding=_embedding(data.title, data.text),
        ),
    )
    _new_version(session, item, reason="created", created_by=data.created_by)
    return item


def upsert_imported_item(
    session: Session,
    *,
    project_id: uuid.UUID,
    artifact_id: uuid.UUID | None,
    key: str,
    type_: ItemType,
    title: str,
    text: str,
    source_locator_id: uuid.UUID,
    created_by: str,
) -> tuple[ArtifactItemRecord, bool]:
    existing = (
        item_repo.get_by_artifact_key(session, artifact_id, key)
        if artifact_id is not None
        else None
    )
    if existing is None and artifact_id is None:
        existing = next(
            (
                item
                for item in item_repo.list_items(session, project_id, include_stale=True)
                if item.artifact_id is None and item.key == key and item.type == type_.value
            ),
            None,
        )
    if existing is None:
        item = item_repo.add(
            session,
            ArtifactItemRecord(
                project_id=project_id,
                artifact_id=artifact_id,
                key=key,
                type=type_.value,
                title=title,
                text=text,
                status="active",
                source_locator_id=source_locator_id,
                embedding=_embedding(title, text),
            ),
        )
        _new_version(session, item, reason="imported", created_by=created_by)
        return item, True
    changed = (
        existing.title != title
        or existing.text != text
        or existing.source_locator_id != source_locator_id
        or existing.status != "active"
    )
    if changed:
        existing.title = title
        existing.text = text
        existing.status = "active"
        existing.source_locator_id = source_locator_id
        existing.valid_to = None
        existing.embedding = _embedding(title, text)
        _new_version(session, existing, reason="source revision imported", created_by=created_by)
    return existing, changed


def sync_artifact_items(
    session: Session,
    artifact: Artifact,
    *,
    reason: str,
    created_by: str,
) -> list[ArtifactItemRecord]:
    raw_items = artifact.items or []
    if not raw_items:
        raw_items = [
            {
                "key": "DOC",
                "title": artifact.title,
                "text": artifact.content,
                "refs": [],
            }
        ]
    incoming_keys: set[str] = set()
    synced: list[ArtifactItemRecord] = []
    type_ = _ARTIFACT_ITEM_TYPE[artifact.type]
    for raw in raw_items:
        key = str(raw.get("key") or "").strip()
        if not key or key in incoming_keys:
            raise ValidationError("Artifact item keys must be non-empty and unique")
        incoming_keys.add(key)
        item, _ = upsert_imported_item(
            session,
            project_id=artifact.project_id,
            artifact_id=artifact.id,
            key=key,
            type_=type_,
            title=str(raw.get("title") or key),
            text=str(raw.get("text") or ""),
            source_locator_id=artifact.source_locator_id,
            created_by=created_by,
        )
        synced.append(item)

    now = datetime.now(UTC)
    for existing in item_repo.list_for_artifact(session, artifact.id):
        if existing.key not in incoming_keys and existing.valid_to is None:
            existing.status = "stale"
            existing.valid_to = now
            _new_version(session, existing, reason=reason, created_by=created_by)

    for raw in raw_items:
        source_item = item_repo.get_by_artifact_key(session, artifact.id, str(raw.get("key")))
        if source_item is None:
            continue
        for ref in raw.get("refs", []):
            try:
                target_artifact_id = uuid.UUID(str(ref.get("artifact_id")))
            except (TypeError, ValueError, AttributeError):
                continue
            target = item_repo.get_by_artifact_key(
                session, target_artifact_id, str(ref.get("key") or "")
            )
            if target is None:
                continue
            link_type = {
                ItemType.user_story.value: LinkType.refines,
                ItemType.task.value: LinkType.implements,
                ItemType.test.value: LinkType.tests,
            }.get(source_item.type, LinkType.related_to)
            if item_repo.find_link(session, source_item.id, target.id, link_type) is None:
                create_link(
                    session,
                    artifact.project_id,
                    ItemLinkCreate(
                        source_item_id=source_item.id,
                        target_item_id=target.id,
                        type=link_type,
                        origin=LinkOrigin.imported,
                        state=LinkState.confirmed,
                        confidence=1.0,
                        rationale="Imported from the artifact item reference.",
                        created_by=created_by,
                    ),
                )
    return synced


def _link_allowed(source_type: str, target_type: str, type_: LinkType) -> bool:
    if type_ == LinkType.related_to:
        return True
    if type_ == LinkType.depends_on:
        return source_type != ItemType.change_request.value
    if type_ == LinkType.derived_from:
        return source_type != target_type or source_type == ItemType.document.value
    if type_ == LinkType.changes:
        return source_type in {
            ItemType.change_request.value,
            ItemType.commit.value,
            ItemType.pull_request.value,
        }
    return (source_type, target_type) in _ALLOWED_LINKS.get(type_, set())


def create_link(session: Session, project_id: uuid.UUID, data: ItemLinkCreate) -> ItemLink:
    if data.source_item_id == data.target_item_id:
        raise ValidationError("An item link cannot point to itself")
    source = item_repo.get(session, data.source_item_id, project_id)
    target = item_repo.get(session, data.target_item_id, project_id)
    if source is None or target is None:
        raise NotFoundError("Both linked items must belong to the selected project")
    if not _link_allowed(source.type, target.type, data.type):
        raise ValidationError(
            f"Link '{data.type.value}' is not valid from '{source.type}' to '{target.type}'"
        )
    if data.origin == LinkOrigin.inferred and data.state == LinkState.confirmed:
        raise ValidationError("An inferred link must be reviewed before it can be confirmed")
    if (
        data.source_revision_id is not None
        and source_repo.get_revision(session, project_id, data.source_revision_id) is None
    ):
        raise ValidationError("Link source revision does not belong to the selected project")
    if item_repo.find_link(session, source.id, target.id, data.type) is not None:
        raise ConflictError("An identical item link already exists")
    evidence_locator_ids = list(dict.fromkeys(data.evidence_locator_ids))
    if not evidence_locator_ids:
        fallback = source.source_locator_id or target.source_locator_id
        if fallback is None:
            raise ValidationError("An item link requires source evidence")
        evidence_locator_ids = [fallback]
    for locator_id in evidence_locator_ids:
        provenance_service.require_locator(session, project_id, locator_id)
    confirmed = data.state == LinkState.confirmed
    link = item_repo.add(
        session,
        ItemLink(
            project_id=project_id,
            source_item_id=source.id,
            target_item_id=target.id,
            type=data.type,
            origin=data.origin.value,
            confidence=data.confidence,
            rationale=data.rationale,
            evidence_locator_ids=[str(value) for value in evidence_locator_ids],
            state=data.state.value,
            source_revision_id=data.source_revision_id,
            confirmed_by=data.created_by if confirmed else None,
            confirmed_at=datetime.now(UTC) if confirmed else None,
        ),
    )
    for locator_id in evidence_locator_ids:
        session.add(
            EvidenceRef(
                project_id=project_id,
                source_locator_id=locator_id,
                subject_type="item_link",
                subject_id=link.id,
                excerpt=data.rationale[:1000] or None,
                digest=hashlib.sha256(data.rationale.encode()).hexdigest(),
            )
        )
    return link


def review_link(
    session: Session,
    project_id: uuid.UUID,
    link_id: uuid.UUID,
    data: ItemLinkReview,
) -> ItemLink:
    link = item_repo.get_link(session, project_id, link_id)
    if link is None:
        raise NotFoundError(f"Item link {link_id} not found")
    if data.state not in {LinkState.confirmed, LinkState.rejected}:
        raise ValidationError("Review must confirm or reject the proposed item link")
    if link.state != LinkState.proposed.value:
        raise ConflictError("Only a proposed item link can be reviewed")
    link.state = data.state.value
    link.confirmed_by = data.reviewed_by if data.state == LinkState.confirmed else None
    link.confirmed_at = datetime.now(UTC) if data.state == LinkState.confirmed else None
    session.flush()
    return link


def get_item(session: Session, project_id: uuid.UUID, item_id: uuid.UUID) -> ArtifactItemRecord:
    item = item_repo.get(session, item_id, project_id)
    if item is None:
        raise NotFoundError(f"Item {item_id} not found in project {project_id}")
    return item


def update_item(
    session: Session,
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    data: ItemUpdate,
) -> ArtifactItemRecord:
    item = get_item(session, project_id, item_id)
    changed = False
    content_changed = False
    if data.title is not None and data.title != item.title:
        item.title = data.title
        changed = content_changed = True
    if data.text is not None and data.text != item.text:
        item.text = data.text
        changed = content_changed = True
    if data.status is not None and data.status != item.status:
        item.status = data.status
        changed = True
    if data.source_locator_id is not None and data.source_locator_id != item.source_locator_id:
        provenance_service.require_locator(session, project_id, data.source_locator_id)
        item.source_locator_id = data.source_locator_id
        changed = True
    elif content_changed:
        locator = provenance_service.ensure_manual_locator(
            session,
            project_id,
            label=item.title,
            content=f"{item.title}\n{item.text}",
            source_ref=None,
            created_by=data.updated_by,
        )
        item.source_locator_id = locator.id
    if not changed:
        return item
    item.valid_to = datetime.now(UTC) if item.status == "stale" else None
    item.embedding = _embedding(item.title, item.text)
    _new_version(session, item, reason=data.reason, created_by=data.updated_by)
    mark_links_stale(session, project_id, {item.id})
    session.flush()
    return item


def mark_links_stale(session: Session, project_id: uuid.UUID, item_ids: set[uuid.UUID]) -> int:
    changed = 0
    for link in item_repo.links_touching(session, project_id, item_ids):
        if link.state == LinkState.confirmed.value:
            link.state = LinkState.stale.value
            changed += 1
    return changed


def mark_item_stale(
    session: Session,
    item: ArtifactItemRecord,
    *,
    source_locator_id: uuid.UUID,
    reason: str,
    created_by: str,
) -> ItemVersion:
    item.status = "stale"
    item.valid_to = datetime.now(UTC)
    item.source_locator_id = source_locator_id
    item.embedding = _embedding(item.title, item.text)
    return _new_version(session, item, reason=reason, created_by=created_by)
