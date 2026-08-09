"""First-class knowledge-item API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from engram.enums import ItemType, LinkOrigin, LinkState, LinkType


class ItemCreate(BaseModel):
    artifact_id: uuid.UUID | None = None
    key: str = Field(min_length=1, max_length=200)
    type: ItemType
    title: str = Field(min_length=1, max_length=500)
    text: str = ""
    status: str = "active"
    source_locator_id: uuid.UUID
    created_by: str = "system"


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    artifact_id: uuid.UUID | None
    key: str
    type: str
    title: str
    text: str
    status: str
    current_version_id: uuid.UUID | None
    source_locator_id: uuid.UUID | None
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime
    updated_at: datetime


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    text: str | None = None
    status: str | None = None
    source_locator_id: uuid.UUID | None = None
    reason: str = "manual item update"
    updated_by: str = "system"


class ItemVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    version: int
    title: str
    text: str
    status: str
    source_revision_id: uuid.UUID | None
    source_locator_id: uuid.UUID | None
    reason: str | None
    is_active: bool
    created_at: datetime
    created_by: str


class ItemLinkCreate(BaseModel):
    source_item_id: uuid.UUID
    target_item_id: uuid.UUID
    type: LinkType
    origin: LinkOrigin = LinkOrigin.manual
    confidence: float = Field(default=1.0, ge=0, le=1)
    rationale: str = ""
    evidence_locator_ids: list[uuid.UUID] = Field(default_factory=list)
    state: LinkState = LinkState.confirmed
    source_revision_id: uuid.UUID | None = None
    created_by: str = "system"


class ItemLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_item_id: uuid.UUID
    target_item_id: uuid.UUID
    type: LinkType
    origin: str
    confidence: float
    rationale: str
    evidence_locator_ids: list[uuid.UUID]
    state: str
    source_revision_id: uuid.UUID | None
    confirmed_by: str | None
    confirmed_at: datetime | None
    created_at: datetime


class ItemLinkReview(BaseModel):
    state: LinkState
    reviewed_by: str = "system"
