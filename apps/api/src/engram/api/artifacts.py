"""CRUD endpoints for artifacts, their versions, and their links."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from engram.db.session import get_session
from engram.enums import ArtifactStatus, ArtifactType
from engram.repositories import artifact_repo
from engram.schemas.artifact import (
    ArtifactCreate,
    ArtifactRead,
    ArtifactUpdate,
    ArtifactVersionRead,
)
from engram.schemas.link import LinkRead
from engram.services import artifact_service, link_service, project_service

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.post("", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED)
def create_artifact(data: ArtifactCreate, session: Session = Depends(get_session)) -> ArtifactRead:
    artifact = artifact_service.create_artifact(session, data)
    session.commit()
    return artifact


@router.get("", response_model=list[ArtifactRead])
def list_artifacts(
    session: Session = Depends(get_session),
    type_: ArtifactType | None = Query(default=None, alias="type"),
    status_: ArtifactStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ArtifactRead]:
    project_id = project_service.ensure_default_project(session).id
    return artifact_repo.list_artifacts(
        session,
        project_id=project_id,
        type_=type_,
        status=status_,
        limit=limit,
        offset=offset,
    )


@router.get("/{artifact_id}", response_model=ArtifactRead)
def get_artifact(artifact_id: uuid.UUID, session: Session = Depends(get_session)) -> ArtifactRead:
    project_id = project_service.ensure_default_project(session).id
    return artifact_service.get_artifact(session, artifact_id, project_id)


@router.patch("/{artifact_id}", response_model=ArtifactRead)
def update_artifact(
    artifact_id: uuid.UUID, data: ArtifactUpdate, session: Session = Depends(get_session)
) -> ArtifactRead:
    project_id = project_service.ensure_default_project(session).id
    artifact_service.get_artifact(session, artifact_id, project_id)
    artifact = artifact_service.update_artifact(session, artifact_id, data)
    session.commit()
    return artifact


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(artifact_id: uuid.UUID, session: Session = Depends(get_session)) -> None:
    project_id = project_service.ensure_default_project(session).id
    artifact_service.delete_artifact(session, artifact_id, project_id)
    session.commit()


@router.get("/{artifact_id}/versions", response_model=list[ArtifactVersionRead])
def list_versions(
    artifact_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[ArtifactVersionRead]:
    project_id = project_service.ensure_default_project(session).id
    artifact_service.get_artifact(session, artifact_id, project_id)
    return artifact_service.list_versions(session, artifact_id)


@router.get("/{artifact_id}/links", response_model=list[LinkRead])
def list_links(artifact_id: uuid.UUID, session: Session = Depends(get_session)) -> list[LinkRead]:
    project_id = project_service.ensure_default_project(session).id
    artifact_service.get_artifact(session, artifact_id, project_id)
    return link_service.list_links_for_artifact(session, artifact_id)
