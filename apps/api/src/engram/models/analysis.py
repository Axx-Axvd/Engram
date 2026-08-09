"""Persisted impact analyses, context packages and causal change sets."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from engram.db.base import Base


class ImpactAnalysis(Base):
    __tablename__ = "impact_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    source_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    request_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="in_review", index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    model_provider: Mapped[str] = mapped_column(String(100), default="mock")
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(50), default="impact-v1")
    retrieval_mode: Mapped[str] = mapped_column(String(30), default="combined", index=True)
    context_budget: Mapped[int] = mapped_column(Integer, default=4000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200), default="system")


class ImpactCandidate(Base):
    __tablename__ = "impact_candidates"
    __table_args__ = (
        UniqueConstraint("analysis_id", "item_id", name="uq_analysis_candidate_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_analyses.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifact_items.id", ondelete="CASCADE"), index=True
    )
    item_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item_versions.id", ondelete="CASCADE"), index=True
    )
    impact_type: Mapped[str] = mapped_column(String(30), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    proposed_action: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    selection_reason: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    decision: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContextPackage(Base):
    __tablename__ = "context_packages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_analyses.id", ondelete="CASCADE"), index=True
    )
    token_budget: Mapped[int] = mapped_column(Integer)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200), default="system")


class ContextPackageItem(Base):
    __tablename__ = "context_package_items"
    __table_args__ = (
        UniqueConstraint("package_id", "item_version_id", name="uq_package_item_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("context_packages.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifact_items.id", ondelete="CASCADE"), index=True
    )
    item_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item_versions.id", ondelete="CASCADE"), index=True
    )
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    token_estimate: Mapped[int] = mapped_column(Integer)
    reason: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    graph_path: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")


class ChangeSet(Base):
    __tablename__ = "change_sets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("impact_analyses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(300), index=True)
    external_url: Mapped[str | None] = mapped_column(String(1500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="imported")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChangeSetItem(Base):
    __tablename__ = "change_set_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    change_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("change_sets.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifact_items.id", ondelete="CASCADE"), index=True
    )
    before_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("item_versions.id", ondelete="SET NULL"), nullable=True
    )
    after_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("item_versions.id", ondelete="SET NULL"), nullable=True
    )
    change_kind: Mapped[str] = mapped_column(String(30), default="modified")
