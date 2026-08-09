"""Creation and validation of immutable source provenance."""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.orm import Session

from engram.enums import SourceKind
from engram.errors import NotFoundError, ValidationError
from engram.models import Source, SourceLocator, SourceRevision
from engram.repositories import source_repo
from engram.schemas.source import SourceCreate
from engram.services import project_service

_MANUAL_SOURCE_NAME = "Manual and legacy input"


def create_source(session: Session, project_id: uuid.UUID, data: SourceCreate) -> Source:
    project_service.get_project(session, project_id)
    existing = source_repo.get_by_name(session, project_id, data.name)
    if existing is not None:
        raise ValidationError(f"Source '{data.name}' already exists in this project")
    return source_repo.add(
        session,
        Source(
            project_id=project_id,
            kind=data.kind.value,
            name=data.name,
            url=data.url,
            configuration=data.configuration,
            created_by=data.created_by,
        ),
    )


def get_source(session: Session, project_id: uuid.UUID, source_id: uuid.UUID) -> Source:
    source = source_repo.get(session, source_id, project_id)
    if source is None:
        raise NotFoundError(f"Source {source_id} not found in project {project_id}")
    return source


def create_revision(
    session: Session,
    source: Source,
    revision: str,
    *,
    revision_url: str | None = None,
    metadata: dict | None = None,
) -> SourceRevision:
    existing = source_repo.find_revision(session, source.id, revision)
    if existing is not None:
        return existing
    return source_repo.add(
        session,
        SourceRevision(
            project_id=source.project_id,
            source_id=source.id,
            revision=revision,
            revision_url=revision_url,
            metadata_json=metadata or {},
        ),
    )


def create_locator(
    session: Session,
    revision: SourceRevision,
    *,
    kind: str,
    path: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    url: str | None = None,
    external_id: str | None = None,
    content: str | None = None,
) -> SourceLocator:
    return source_repo.add(
        session,
        SourceLocator(
            project_id=revision.project_id,
            source_revision_id=revision.id,
            kind=kind,
            path=path,
            start_line=start_line,
            end_line=end_line,
            url=url,
            external_id=external_id,
            content_hash=(
                hashlib.sha256(content.encode()).hexdigest() if content is not None else None
            ),
        ),
    )


def ensure_manual_locator(
    session: Session,
    project_id: uuid.UUID,
    *,
    label: str,
    content: str,
    source_ref: str | None,
    created_by: str,
) -> SourceLocator:
    source = source_repo.get_by_name(session, project_id, _MANUAL_SOURCE_NAME)
    if source is None:
        source = source_repo.add(
            session,
            Source(
                project_id=project_id,
                kind=SourceKind.manual.value,
                name=_MANUAL_SOURCE_NAME,
                configuration={},
                created_by=created_by,
            ),
        )
    revision_key = f"manual:{uuid.uuid4()}"
    revision = create_revision(
        session,
        source,
        revision_key,
        metadata={"legacy_source_ref": source_ref, "created_by": created_by},
    )
    return create_locator(
        session,
        revision,
        kind="manual",
        path=label,
        external_id=source_ref,
        content=content,
    )


def require_locator(
    session: Session, project_id: uuid.UUID, locator_id: uuid.UUID
) -> SourceLocator:
    locator = source_repo.get_locator(session, locator_id)
    if locator is None or locator.project_id != project_id:
        raise ValidationError("Source locator does not belong to the selected project")
    return locator
