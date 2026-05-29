"""Pydantic schemas for artifacts (documents), their items, and their versions."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from engram.enums import ArtifactStatus, ArtifactType, status_allowed_for_type


class ItemRef(BaseModel):
    """A reference from one document's item to an item in another document."""

    artifact_id: uuid.UUID
    key: str


class ArtifactItem(BaseModel):
    """A single structured entry inside a document (e.g. requirement R1, task T2)."""

    key: str
    title: str
    text: str = ""
    feature: str | None = None
    refs: list[ItemRef] = Field(default_factory=list)


class ArtifactCreate(BaseModel):
    type: ArtifactType
    title: str = Field(min_length=1, max_length=500)
    content: str = ""
    items: list[ArtifactItem] = Field(default_factory=list)
    status: ArtifactStatus | None = None
    source_ref: str | None = None
    created_by: str = "system"

    @model_validator(mode="after")
    def _status_matches_type(self) -> ArtifactCreate:
        if self.status is not None and not status_allowed_for_type(self.type, self.status):
            raise ValueError(
                f"status '{self.status.value}' is not valid for type '{self.type.value}'"
            )
        return self


class ArtifactUpdate(BaseModel):
    """A partial update. Any provided field produces a new artifact version."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
    items: list[ArtifactItem] | None = None
    status: ArtifactStatus | None = None
    source_ref: str | None = None
    reason: str | None = None
    updated_by: str = "system"


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ArtifactType
    title: str
    content: str
    items: list[ArtifactItem] = Field(default_factory=list)
    status: ArtifactStatus
    current_version: int
    source_ref: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str


class ArtifactVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    version: int
    title: str
    content: str
    items: list[ArtifactItem] = Field(default_factory=list)
    status: ArtifactStatus
    reason: str | None
    is_active: bool
    created_at: datetime
    created_by: str
