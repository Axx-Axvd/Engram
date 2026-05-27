"""Consistency report endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from engram.db.session import get_session
from engram.schemas.consistency import ConsistencyReport
from engram.services import consistency_service

router = APIRouter(prefix="/api/consistency", tags=["consistency"])


@router.get("", response_model=ConsistencyReport)
def get_consistency(session: Session = Depends(get_session)) -> ConsistencyReport:
    return consistency_service.check_consistency(session)
