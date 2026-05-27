"""Endpoints for artifact links."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from engram.db.session import get_session
from engram.repositories import link_repo
from engram.schemas.link import LinkCreate, LinkRead
from engram.services import link_service

router = APIRouter(prefix="/api/links", tags=["links"])


@router.get("", response_model=list[LinkRead])
def list_links(session: Session = Depends(get_session)) -> list[LinkRead]:
    """All links in the project (used by the relationships graph)."""
    return link_repo.list_all(session)


@router.post("", response_model=LinkRead, status_code=status.HTTP_201_CREATED)
def create_link(data: LinkCreate, session: Session = Depends(get_session)) -> LinkRead:
    link = link_service.create_link(session, data)
    session.commit()
    return link
