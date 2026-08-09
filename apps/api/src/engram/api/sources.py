"""Project-scoped source and read-only GitHub sync endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from engram.db.session import get_session
from engram.repositories import source_repo
from engram.schemas.source import (
    GitHubSourceCreate,
    SourceRead,
    SourceRevisionRead,
    SourceSyncRequest,
    SourceSyncResult,
)
from engram.services import github_source_service, project_service, provenance_service

router = APIRouter(prefix="/api/projects/{project_id}/sources", tags=["sources"])


@router.get("", response_model=list[SourceRead])
def list_sources(
    project_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[SourceRead]:
    project_service.get_project(session, project_id)
    return source_repo.list_sources(session, project_id)


@router.post("/github", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_github_source(
    project_id: uuid.UUID,
    data: GitHubSourceCreate,
    session: Session = Depends(get_session),
) -> SourceRead:
    source = github_source_service.create_github_source(session, project_id, data)
    session.commit()
    return source


@router.get("/{source_id}/revisions", response_model=list[SourceRevisionRead])
def list_revisions(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[SourceRevisionRead]:
    provenance_service.get_source(session, project_id, source_id)
    return source_repo.list_revisions(session, source_id)


@router.post("/{source_id}/sync", response_model=SourceSyncResult)
def sync_source(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    data: SourceSyncRequest,
    session: Session = Depends(get_session),
) -> SourceSyncResult:
    result = github_source_service.sync_github_source(
        session,
        project_id,
        source_id,
        ref=data.ref,
        analysis_id=data.analysis_id,
        created_by=data.created_by,
    )
    session.commit()
    return result
