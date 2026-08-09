"""Artifact and ArtifactVersion ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engram.config import settings
from engram.db.base import Base
from engram.enums import ArtifactStatus, ArtifactType

# Shared native-enum types (reused across columns so the PG type is created once).
artifact_type_enum = SAEnum(ArtifactType, name="artifact_type")
artifact_status_enum = SAEnum(ArtifactStatus, name="artifact_status")


class Artifact(Base):
    """Current ("head") state of a project-memory artifact."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[ArtifactType] = mapped_column(artifact_type_enum, index=True)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, default="")
    items: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    status: Mapped[ArtifactStatus] = mapped_column(
        artifact_status_enum, default=ArtifactStatus.draft, index=True
    )
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_locator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_locators.id", ondelete="SET NULL"), nullable=True, index=True
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(200), default="system")
    updated_by: Mapped[str] = mapped_column(String(200), default="system")

    versions: Mapped[list[ArtifactVersion]] = relationship(
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="ArtifactVersion.version",
    )


class ArtifactVersion(Base):
    """Immutable snapshot of an artifact at a given version. Exactly one is active."""

    __tablename__ = "artifact_versions"
    __table_args__ = (UniqueConstraint("artifact_id", "version", name="uq_artifact_version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, default="")
    items: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    status: Mapped[ArtifactStatus] = mapped_column(artifact_status_enum)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200), default="system")

    artifact: Mapped[Artifact] = relationship(back_populates="versions")
