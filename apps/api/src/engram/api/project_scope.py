"""Project-scoped compatibility and first-class knowledge endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from engram.db.session import get_session
from engram.enums import ArtifactStatus, ArtifactType
from engram.orchestration import get_workflow_engine
from engram.repositories import artifact_repo, item_repo, link_repo
from engram.schemas.artifact import (
    ArtifactCreate,
    ArtifactRead,
    ArtifactUpdate,
    ArtifactVersionRead,
)
from engram.schemas.consistency import ConsistencyReport
from engram.schemas.item import (
    ItemCreate,
    ItemLinkCreate,
    ItemLinkRead,
    ItemLinkReview,
    ItemRead,
    ItemUpdate,
    ItemVersionRead,
)
from engram.schemas.link import LinkCreate, LinkRead
from engram.schemas.search import ContextBundle, ContextQuery
from engram.schemas.workflow import FormalizeRequest, FormalizeResult
from engram.services import (
    artifact_service,
    consistency_service,
    context_service,
    item_service,
    link_service,
    project_service,
)

router = APIRouter(prefix="/api/projects/{project_id}", tags=["project knowledge"])


@router.get("/artifacts", response_model=list[ArtifactRead])
def list_artifacts(
    project_id: uuid.UUID,
    session: Session = Depends(get_session),
    type_: ArtifactType | None = Query(default=None, alias="type"),
    status_: ArtifactStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ArtifactRead]:
    project_service.get_project(session, project_id)
    return artifact_repo.list_artifacts(
        session,
        project_id=project_id,
        type_=type_,
        status=status_,
        limit=limit,
        offset=offset,
    )


@router.post("/artifacts", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED)
def create_artifact(
    project_id: uuid.UUID,
    data: ArtifactCreate,
    session: Session = Depends(get_session),
) -> ArtifactRead:
    artifact = artifact_service.create_artifact(
        session, data.model_copy(update={"project_id": project_id})
    )
    session.commit()
    return artifact


@router.get("/artifacts/{artifact_id}", response_model=ArtifactRead)
def get_artifact(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ArtifactRead:
    return artifact_service.get_artifact(session, artifact_id, project_id)


@router.patch("/artifacts/{artifact_id}", response_model=ArtifactRead)
def update_artifact(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    data: ArtifactUpdate,
    session: Session = Depends(get_session),
) -> ArtifactRead:
    artifact_service.get_artifact(session, artifact_id, project_id)
    artifact = artifact_service.update_artifact(session, artifact_id, data)
    session.commit()
    return artifact


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> None:
    artifact_service.delete_artifact(session, artifact_id, project_id)
    session.commit()


@router.get("/artifacts/{artifact_id}/versions", response_model=list[ArtifactVersionRead])
def list_artifact_versions(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[ArtifactVersionRead]:
    artifact_service.get_artifact(session, artifact_id, project_id)
    return artifact_repo.list_versions(session, artifact_id)


@router.get("/artifacts/{artifact_id}/links", response_model=list[LinkRead])
def list_links_for_artifact(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[LinkRead]:
    artifact_service.get_artifact(session, artifact_id, project_id)
    return link_service.list_links_for_artifact(session, artifact_id)


@router.get("/links", response_model=list[LinkRead])
def list_artifact_links(
    project_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[LinkRead]:
    project_service.get_project(session, project_id)
    return link_repo.list_all(session, project_id)


@router.post("/links", response_model=LinkRead, status_code=status.HTTP_201_CREATED)
def create_artifact_link(
    project_id: uuid.UUID,
    data: LinkCreate,
    session: Session = Depends(get_session),
) -> LinkRead:
    link = link_service.create_link(session, data.model_copy(update={"project_id": project_id}))
    session.commit()
    return link


@router.get("/items", response_model=list[ItemRead])
def list_items(
    project_id: uuid.UUID,
    include_stale: bool = False,
    session: Session = Depends(get_session),
) -> list[ItemRead]:
    project_service.get_project(session, project_id)
    return item_repo.list_items(session, project_id, include_stale=include_stale)


@router.post("/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    project_id: uuid.UUID,
    data: ItemCreate,
    session: Session = Depends(get_session),
) -> ItemRead:
    item = item_service.create_item(session, project_id, data)
    session.commit()
    return item


@router.get("/items/{item_id}", response_model=ItemRead)
def get_item(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ItemRead:
    return item_service.get_item(session, project_id, item_id)


@router.patch("/items/{item_id}", response_model=ItemRead)
def update_item(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    data: ItemUpdate,
    session: Session = Depends(get_session),
) -> ItemRead:
    item = item_service.update_item(session, project_id, item_id, data)
    session.commit()
    return item


@router.get("/items/{item_id}/versions", response_model=list[ItemVersionRead])
def list_item_versions(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> list[ItemVersionRead]:
    item_service.get_item(session, project_id, item_id)
    return item_repo.list_versions(session, item_id)


@router.get("/item-links", response_model=list[ItemLinkRead])
def list_item_links(
    project_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[ItemLinkRead]:
    project_service.get_project(session, project_id)
    return item_repo.list_links(session, project_id)


@router.post("/item-links", response_model=ItemLinkRead, status_code=status.HTTP_201_CREATED)
def create_item_link(
    project_id: uuid.UUID,
    data: ItemLinkCreate,
    session: Session = Depends(get_session),
) -> ItemLinkRead:
    link = item_service.create_link(session, project_id, data)
    session.commit()
    return link


@router.patch("/item-links/{link_id}", response_model=ItemLinkRead)
def review_item_link(
    project_id: uuid.UUID,
    link_id: uuid.UUID,
    data: ItemLinkReview,
    session: Session = Depends(get_session),
) -> ItemLinkRead:
    link = item_service.review_link(session, project_id, link_id, data)
    session.commit()
    return link


@router.post("/search/context", response_model=ContextBundle)
def search_context(
    project_id: uuid.UUID,
    data: ContextQuery,
    session: Session = Depends(get_session),
) -> ContextBundle:
    return context_service.select_context(
        session, data.model_copy(update={"project_id": project_id})
    )


@router.get("/consistency", response_model=ConsistencyReport)
def get_consistency(
    project_id: uuid.UUID, session: Session = Depends(get_session)
) -> ConsistencyReport:
    return consistency_service.check_consistency(session, project_id)


@router.post(
    "/workflows/formalize",
    response_model=FormalizeResult,
    status_code=status.HTTP_201_CREATED,
)
def formalize(
    project_id: uuid.UUID,
    data: FormalizeRequest,
    session: Session = Depends(get_session),
) -> FormalizeResult:
    result = get_workflow_engine().formalize(
        session, data.model_copy(update={"project_id": project_id})
    )
    session.commit()
    return result
