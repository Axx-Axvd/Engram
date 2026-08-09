"""Source, revision and locator API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from engram.enums import SourceKind


class SourceCreate(BaseModel):
    kind: SourceKind
    name: str = Field(min_length=1, max_length=300)
    url: str | None = None
    configuration: dict = Field(default_factory=dict)
    created_by: str = "system"


class GitHubSourceCreate(BaseModel):
    repository: str = Field(pattern=r"^[^/\s]+/[^/\s]+$")
    ref: str = "main"
    created_by: str = "system"


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    kind: str
    name: str
    url: str | None
    configuration: dict
    created_at: datetime
    created_by: str


class SourceRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_id: uuid.UUID
    revision: str
    revision_url: str | None
    metadata_json: dict
    captured_at: datetime


class SourceLocatorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_revision_id: uuid.UUID
    kind: str
    path: str | None
    start_line: int | None
    end_line: int | None
    url: str | None
    external_id: str | None
    content_hash: str | None


class SourceSyncResult(BaseModel):
    source: SourceRead
    revision: SourceRevisionRead
    imported_items: int
    updated_items: int
    deleted_items: int
    stale_links: int
    change_set_id: uuid.UUID | None = None


class SourceSyncRequest(BaseModel):
    ref: str | None = None
    analysis_id: uuid.UUID | None = None
    created_by: str = "system"
