"""Schemas for the consistency report."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel

Severity = Literal["error", "warning"]


class ConsistencyIssue(BaseModel):
    severity: Severity
    code: str
    message: str
    artifact_id: uuid.UUID | None = None
    artifact_title: str | None = None
    item_key: str | None = None


class ConsistencyReport(BaseModel):
    ok: bool
    errors: int
    warnings: int
    checked_artifacts: int
    issues: list[ConsistencyIssue]
