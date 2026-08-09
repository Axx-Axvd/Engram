"""Schemas for context retrieval."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from engram.schemas.artifact import ArtifactRead
from engram.schemas.link import LinkRead


class ContextQuery(BaseModel):
    project_id: uuid.UUID | None = None
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=50)
    hops: int = Field(default=1, ge=0, le=3)
    exclude_archived: bool = True
    token_budget: int = Field(default=4000, ge=128, le=100_000)


class ContextBundle(BaseModel):
    """A minimal slice of project memory relevant to a query."""

    seed_ids: list[uuid.UUID]
    artifacts: list[ArtifactRead]
    links: list[LinkRead]
