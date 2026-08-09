"""ChangeLog ORM model — append-only record of what happened to artifacts."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from engram.db.base import Base
from engram.enums import ChangeAction

change_action_enum = SAEnum(ChangeAction, name="change_action")


class ChangeLog(Base):
    __tablename__ = "change_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    action: Mapped[ChangeAction] = mapped_column(change_action_enum)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200), default="system")
