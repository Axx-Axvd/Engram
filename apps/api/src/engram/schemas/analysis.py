"""Impact-analysis, context-package and ChangeSet contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from engram.enums import RetrievalMode, ReviewDecision
from engram.schemas.item import ItemRead, ItemVersionRead
from engram.schemas.source import SourceLocatorRead


class ImpactAnalysisCreate(BaseModel):
    query: str = Field(min_length=1)
    source_revision_id: uuid.UUID | None = None
    context_budget: int = Field(default=4000, ge=128, le=100_000)
    max_candidates: int = Field(default=20, ge=1, le=100)
    retrieval_mode: RetrievalMode = RetrievalMode.combined
    created_by: str = "system"


class ImpactCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    item_id: uuid.UUID
    item_version_id: uuid.UUID
    impact_type: str
    confidence: float
    rationale: str
    proposed_action: str
    evidence: list[str]
    selection_reason: dict
    decision: str
    reviewed_by: str | None
    reviewed_at: datetime | None


class ImpactAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_revision_id: uuid.UUID | None
    request_text: str
    status: str
    summary: str
    model_provider: str
    model_name: str | None
    algorithm_version: str
    retrieval_mode: str
    context_budget: int
    created_at: datetime
    created_by: str
    candidates: list[ImpactCandidateRead] = Field(default_factory=list)


class CandidateReview(BaseModel):
    decision: ReviewDecision
    reviewed_by: str = "system"


class ContextPackageCreate(BaseModel):
    token_budget: int = Field(default=4000, ge=128, le=100_000)
    created_by: str = "system"


class ContextPackageItemRead(BaseModel):
    item: ItemRead
    version: ItemVersionRead
    source_locator: SourceLocatorRead | None
    rank: int
    score: float
    token_estimate: int
    reason: dict
    graph_path: list[dict]


class ContextPackageRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    analysis_id: uuid.UUID
    token_budget: int
    token_estimate: int
    created_at: datetime
    created_by: str
    items: list[ContextPackageItemRead]


class ChangeSetItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    change_set_id: uuid.UUID
    item_id: uuid.UUID
    before_version_id: uuid.UUID | None
    after_version_id: uuid.UUID | None
    change_kind: str


class ChangeSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    analysis_id: uuid.UUID | None
    source_revision_id: uuid.UUID
    external_id: str
    external_url: str | None
    status: str
    summary: str
    created_at: datetime
    items: list[ChangeSetItemRead] = Field(default_factory=list)
