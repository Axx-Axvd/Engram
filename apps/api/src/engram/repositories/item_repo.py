"""Knowledge-item persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from engram.models import ArtifactItemRecord, ItemLink, ItemVersion


def get(session: Session, item_id: uuid.UUID, project_id: uuid.UUID) -> ArtifactItemRecord | None:
    return session.scalars(
        select(ArtifactItemRecord).where(
            ArtifactItemRecord.id == item_id,
            ArtifactItemRecord.project_id == project_id,
        )
    ).first()


def get_by_artifact_key(
    session: Session, artifact_id: uuid.UUID, key: str
) -> ArtifactItemRecord | None:
    return session.scalars(
        select(ArtifactItemRecord).where(
            ArtifactItemRecord.artifact_id == artifact_id,
            ArtifactItemRecord.key == key,
        )
    ).first()


def list_items(
    session: Session, project_id: uuid.UUID, *, include_stale: bool = False
) -> list[ArtifactItemRecord]:
    stmt = select(ArtifactItemRecord).where(ArtifactItemRecord.project_id == project_id)
    if not include_stale:
        stmt = stmt.where(ArtifactItemRecord.valid_to.is_(None))
    return list(session.scalars(stmt.order_by(ArtifactItemRecord.created_at)))


def list_for_artifact(session: Session, artifact_id: uuid.UUID) -> list[ArtifactItemRecord]:
    return list(
        session.scalars(
            select(ArtifactItemRecord).where(ArtifactItemRecord.artifact_id == artifact_id)
        )
    )


def current_version(session: Session, item: ArtifactItemRecord) -> ItemVersion | None:
    if item.current_version_id is None:
        return None
    return session.get(ItemVersion, item.current_version_id)


def list_versions(session: Session, item_id: uuid.UUID) -> list[ItemVersion]:
    return list(
        session.scalars(
            select(ItemVersion).where(ItemVersion.item_id == item_id).order_by(ItemVersion.version)
        )
    )


def list_links(session: Session, project_id: uuid.UUID) -> list[ItemLink]:
    return list(session.scalars(select(ItemLink).where(ItemLink.project_id == project_id)))


def get_link(session: Session, project_id: uuid.UUID, link_id: uuid.UUID) -> ItemLink | None:
    return session.scalars(
        select(ItemLink).where(ItemLink.id == link_id, ItemLink.project_id == project_id)
    ).first()


def links_touching(
    session: Session, project_id: uuid.UUID, item_ids: set[uuid.UUID]
) -> list[ItemLink]:
    if not item_ids:
        return []
    return list(
        session.scalars(
            select(ItemLink).where(
                ItemLink.project_id == project_id,
                or_(
                    ItemLink.source_item_id.in_(item_ids),
                    ItemLink.target_item_id.in_(item_ids),
                ),
            )
        )
    )


def find_link(
    session: Session,
    source_item_id: uuid.UUID,
    target_item_id: uuid.UUID,
    type_,
) -> ItemLink | None:
    return session.scalars(
        select(ItemLink).where(
            ItemLink.source_item_id == source_item_id,
            ItemLink.target_item_id == target_item_id,
            ItemLink.type == type_,
        )
    ).first()


def add(session: Session, value):
    session.add(value)
    session.flush()
    return value
