"""Context-retrieval endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from engram.db.session import get_session
from engram.schemas.search import ContextBundle, ContextQuery
from engram.services import context_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/context", response_model=ContextBundle)
def search_context(query: ContextQuery, session: Session = Depends(get_session)) -> ContextBundle:
    return context_service.select_context(session, query)
