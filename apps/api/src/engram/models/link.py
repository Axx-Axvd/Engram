"""ArtifactLink ORM model — typed directed edges between artifacts."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from engram.db.base import Base
from engram.enums import LinkType

link_type_enum = SAEnum(LinkType, name="link_type")


class ArtifactLink(Base):
    __tablename__ = "artifact_links"
    __table_args__ = (UniqueConstraint("source_id", "target_id", "type", name="uq_artifact_link"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"), index=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[LinkType] = mapped_column(link_type_enum, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200), default="system")
