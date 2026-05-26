"""Pydantic schemas for artifacts and their versions."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from engram.enums import ArtifactStatus, ArtifactType


class ArtifactCreate(BaseModel):
    type: ArtifactType
    title: str = Field(min_length=1, max_length=500)
    content: str = ""
    status: ArtifactStatus | None = None
    source_ref: str | None = None
    created_by: str = "system"


class ArtifactUpdate(BaseModel):
    """A partial update. Any provided field produces a new artifact version."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
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
    status: ArtifactStatus
    reason: str | None
    is_active: bool
    created_at: datetime
    created_by: str
