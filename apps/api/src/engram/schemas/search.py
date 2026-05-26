"""Schemas for context retrieval."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from engram.schemas.artifact import ArtifactRead
from engram.schemas.link import LinkRead


class ContextQuery(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=50)
    hops: int = Field(default=1, ge=0, le=3)
    exclude_archived: bool = True


class ContextBundle(BaseModel):
    """A minimal slice of project memory relevant to a query."""

    seed_ids: list[uuid.UUID]
    artifacts: list[ArtifactRead]
    links: list[LinkRead]
