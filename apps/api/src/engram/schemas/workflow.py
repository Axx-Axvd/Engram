"""Schemas for orchestration workflows."""

from __future__ import annotations

from pydantic import BaseModel, Field

from engram.schemas.artifact import ArtifactRead
from engram.schemas.link import LinkRead


class FormalizeRequest(BaseModel):
    description: str = Field(min_length=1)
    created_by: str = "system"


class FormalizeResult(BaseModel):
    """Artifacts and links produced by formalizing a project description."""

    artifacts: list[ArtifactRead]
    links: list[LinkRead]
