"""Source and provenance persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from engram.models import Source, SourceLocator, SourceRevision


def get(session: Session, source_id: uuid.UUID, project_id: uuid.UUID) -> Source | None:
    return session.scalars(
        select(Source).where(Source.id == source_id, Source.project_id == project_id)
    ).first()


def get_by_name(session: Session, project_id: uuid.UUID, name: str) -> Source | None:
    return session.scalars(
        select(Source).where(Source.project_id == project_id, Source.name == name)
    ).first()


def list_sources(session: Session, project_id: uuid.UUID) -> list[Source]:
    return list(
        session.scalars(
            select(Source).where(Source.project_id == project_id).order_by(Source.created_at)
        )
    )


def list_revisions(session: Session, source_id: uuid.UUID) -> list[SourceRevision]:
    return list(
        session.scalars(
            select(SourceRevision)
            .where(SourceRevision.source_id == source_id)
            .order_by(SourceRevision.captured_at.desc())
        )
    )


def get_revision(
    session: Session, project_id: uuid.UUID, revision_id: uuid.UUID
) -> SourceRevision | None:
    return session.scalars(
        select(SourceRevision).where(
            SourceRevision.id == revision_id,
            SourceRevision.project_id == project_id,
        )
    ).first()


def find_revision(session: Session, source_id: uuid.UUID, revision: str) -> SourceRevision | None:
    return session.scalars(
        select(SourceRevision).where(
            SourceRevision.source_id == source_id,
            SourceRevision.revision == revision,
        )
    ).first()


def get_locator(session: Session, locator_id: uuid.UUID) -> SourceLocator | None:
    return session.get(SourceLocator, locator_id)


def add(session: Session, value):
    session.add(value)
    session.flush()
    return value
