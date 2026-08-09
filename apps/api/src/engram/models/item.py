"""First-class, independently versioned knowledge items and their typed links."""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from engram.config import settings
from engram.db.base import Base
from engram.enums import LinkType
from engram.models.link import link_type_enum


class ArtifactItemRecord(Base):
    __tablename__ = "artifact_items"
    __table_args__ = (
        UniqueConstraint("project_id", "artifact_id", "key", name="uq_item_artifact_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    key: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "item_versions.id",
            name="fk_item_current_version",
            use_alter=True,
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    source_locator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_locators.id", ondelete="SET NULL"), nullable=True, index=True
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ItemVersion(Base):
    __tablename__ = "item_versions"
    __table_args__ = (UniqueConstraint("item_id", "version", name="uq_item_version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifact_items.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="active")
    source_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_locator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_locators.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200), default="system")


class ItemLink(Base):
    __tablename__ = "item_links"
    __table_args__ = (
        UniqueConstraint("source_item_id", "target_item_id", "type", name="uq_item_link"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    source_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifact_items.id", ondelete="CASCADE"), index=True
    )
    target_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifact_items.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[LinkType] = mapped_column(link_type_enum, index=True)
    origin: Mapped[str] = mapped_column(String(30), default="manual", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_locator_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    state: Mapped[str] = mapped_column(String(30), default="confirmed", index=True)
    source_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
