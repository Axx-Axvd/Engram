"""External sources, immutable revisions, precise locators and evidence."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from engram.db.base import Base


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_source_project_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    configuration: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200), default="system")


class SourceRevision(Base):
    __tablename__ = "source_revisions"
    __table_args__ = (UniqueConstraint("source_id", "revision", name="uq_source_revision"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[str] = mapped_column(String(200), index=True)
    revision_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SourceLocator(Base):
    __tablename__ = "source_locators"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    source_revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30), default="file")
    path: Mapped[str | None] = mapped_column(String(1000), nullable=True, index=True)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str | None] = mapped_column(String(1500), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)


class EvidenceRef(Base):
    __tablename__ = "evidence_refs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    source_locator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_locators.id", ondelete="CASCADE"), index=True
    )
    subject_type: Mapped[str] = mapped_column(String(50), index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(index=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
