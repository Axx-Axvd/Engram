"""Project-scoped impact-analysis and context-package endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from engram.db.session import get_session
from engram.schemas.analysis import (
    CandidateReview,
    ChangeSetRead,
    ContextPackageCreate,
    ContextPackageRead,
    ImpactAnalysisCreate,
    ImpactAnalysisRead,
    ImpactCandidateRead,
)
from engram.services import analysis_service

router = APIRouter(prefix="/api/projects/{project_id}", tags=["impact analyses"])


@router.post(
    "/impact-analyses",
    response_model=ImpactAnalysisRead,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis(
    project_id: uuid.UUID,
    data: ImpactAnalysisCreate,
    session: Session = Depends(get_session),
) -> ImpactAnalysisRead:
    result = analysis_service.create_analysis(session, project_id, data)
    session.commit()
    return result


@router.get("/impact-analyses", response_model=list[ImpactAnalysisRead])
def list_analyses(
    project_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[ImpactAnalysisRead]:
    return analysis_service.list_analyses(session, project_id)


@router.get("/impact-analyses/{analysis_id}", response_model=ImpactAnalysisRead)
def get_analysis(
    project_id: uuid.UUID,
    analysis_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ImpactAnalysisRead:
    return analysis_service.get_analysis(session, project_id, analysis_id)


@router.patch(
    "/impact-analyses/{analysis_id}/candidates/{candidate_id}",
    response_model=ImpactCandidateRead,
)
def review_candidate(
    project_id: uuid.UUID,
    analysis_id: uuid.UUID,
    candidate_id: uuid.UUID,
    data: CandidateReview,
    session: Session = Depends(get_session),
) -> ImpactCandidateRead:
    result = analysis_service.review_candidate(session, project_id, analysis_id, candidate_id, data)
    session.commit()
    return result


@router.post(
    "/impact-analyses/{analysis_id}/context-packages",
    response_model=ContextPackageRead,
    status_code=status.HTTP_201_CREATED,
)
def build_context_package(
    project_id: uuid.UUID,
    analysis_id: uuid.UUID,
    data: ContextPackageCreate,
    session: Session = Depends(get_session),
) -> ContextPackageRead:
    result = analysis_service.build_context_package(
        session,
        project_id,
        analysis_id,
        token_budget=data.token_budget,
        created_by=data.created_by,
    )
    session.commit()
    return result


@router.get("/context-packages/{package_id}", response_model=ContextPackageRead)
def get_context_package(
    project_id: uuid.UUID,
    package_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ContextPackageRead:
    return analysis_service.get_context_package(session, project_id, package_id)


@router.get("/context-packages", response_model=list[ContextPackageRead])
def list_context_packages(
    project_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[ContextPackageRead]:
    return analysis_service.list_context_packages(session, project_id)


@router.get("/change-sets", response_model=list[ChangeSetRead])
def list_change_sets(
    project_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[ChangeSetRead]:
    return analysis_service.list_change_sets(session, project_id)


@router.get("/change-sets/{change_set_id}", response_model=ChangeSetRead)
def get_change_set(
    project_id: uuid.UUID,
    change_set_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ChangeSetRead:
    return analysis_service.get_change_set(session, project_id, change_set_id)
