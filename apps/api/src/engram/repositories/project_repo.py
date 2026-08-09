"""Project persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from engram.models import Project


def get(session: Session, project_id: uuid.UUID) -> Project | None:
    return session.get(Project, project_id)


def get_by_slug(session: Session, slug: str) -> Project | None:
    return session.scalars(select(Project).where(Project.slug == slug)).first()


def list_projects(session: Session) -> list[Project]:
    return list(session.scalars(select(Project).order_by(Project.created_at, Project.name)))


def add(session: Session, project: Project) -> Project:
    session.add(project)
    session.flush()
    return project
