"""Schemas for orchestration workflows."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from engram.schemas.artifact import ArtifactRead
from engram.schemas.link import LinkRead


class FormalizeRequest(BaseModel):
    project_id: uuid.UUID | None = None
    description: str = Field(min_length=1)
    created_by: str = "system"


class FormalizeResult(BaseModel):
    """Artifacts and links produced by formalizing a project description."""

    artifacts: list[ArtifactRead]
    links: list[LinkRead]


class ChangeRequestInput(BaseModel):
    project_id: uuid.UUID | None = None
    text: str = Field(min_length=1)
    created_by: str = "system"
    max_impacted: int = Field(default=5, ge=1, le=20)


class ImpactedArtifact(BaseModel):
    artifact: ArtifactRead
    rationale: str


class ChangeImpactResult(BaseModel):
    """Outcome of analyzing a change request against existing project memory."""

    change_request: ArtifactRead
    summary: str
    impacted: list[ImpactedArtifact]
    links: list[LinkRead]
