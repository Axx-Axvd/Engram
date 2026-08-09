"""Project lifecycle and default-project compatibility."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from engram.errors import ConflictError, NotFoundError
from engram.models import DEFAULT_PROJECT_ID, Project
from engram.repositories import project_repo
from engram.schemas.project import ProjectCreate


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return result[:100] or "project"


def ensure_default_project(session: Session) -> Project:
    project = project_repo.get(session, DEFAULT_PROJECT_ID)
    if project is not None:
        return project
    existing = project_repo.get_by_slug(session, "default")
    if existing is not None:
        return existing
    return project_repo.add(
        session,
        Project(
            id=DEFAULT_PROJECT_ID,
            name="Default project",
            slug="default",
            description="Migrated prototype data and legacy API operations.",
            is_default=True,
            created_by="migration",
        ),
    )


def resolve_project_id(session: Session, project_id: uuid.UUID | None) -> uuid.UUID:
    if project_id is None:
        return ensure_default_project(session).id
    if project_repo.get(session, project_id) is None:
        raise NotFoundError(f"Project {project_id} not found")
    return project_id


def get_project(session: Session, project_id: uuid.UUID) -> Project:
    project = project_repo.get(session, project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    return project


def create_project(session: Session, data: ProjectCreate) -> Project:
    base = _slug(data.slug or data.name)
    slug = base
    suffix = 2
    while project_repo.get_by_slug(session, slug) is not None:
        if data.slug:
            raise ConflictError(f"Project slug '{slug}' already exists")
        slug = f"{base[:95]}-{suffix}"
        suffix += 1
    return project_repo.add(
        session,
        Project(
            name=data.name.strip(),
            slug=slug,
            description=data.description,
            created_by=data.created_by,
        ),
    )
