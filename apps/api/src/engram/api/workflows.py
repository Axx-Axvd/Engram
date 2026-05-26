"""Workflow endpoints (formalization; change-request analysis added later)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from engram.db.session import get_session
from engram.orchestration import get_workflow_engine
from engram.schemas.workflow import FormalizeRequest, FormalizeResult

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("/formalize", response_model=FormalizeResult, status_code=status.HTTP_201_CREATED)
def formalize(
    request: FormalizeRequest, session: Session = Depends(get_session)
) -> FormalizeResult:
    result = get_workflow_engine().formalize(session, request)
    session.commit()
    return result
