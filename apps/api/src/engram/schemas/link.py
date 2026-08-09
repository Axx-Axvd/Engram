"""Pydantic schemas for artifact links."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from engram.enums import LinkType


class LinkCreate(BaseModel):
    project_id: uuid.UUID | None = None
    source_id: uuid.UUID
    target_id: uuid.UUID
    type: LinkType
    created_by: str = "system"


class LinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_id: uuid.UUID
    target_id: uuid.UUID
    type: LinkType
    created_at: datetime
    created_by: str
