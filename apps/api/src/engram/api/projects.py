"""Project management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from engram.db.session import get_session
from engram.repositories import project_repo
from engram.schemas.project import ProjectCreate, ProjectRead
from engram.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, session: Session = Depends(get_session)) -> ProjectRead:
    project = project_service.create_project(session, data)
    session.commit()
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(session: Session = Depends(get_session)) -> list[ProjectRead]:
    project_service.ensure_default_project(session)
    session.commit()
    return project_repo.list_projects(session)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: uuid.UUID, session: Session = Depends(get_session)) -> ProjectRead:
    return project_service.get_project(session, project_id)
