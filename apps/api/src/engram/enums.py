"""Domain enumerations shared by ORM models and Pydantic schemas."""

from __future__ import annotations

from enum import StrEnum


class ArtifactType(StrEnum):
    project_brief = "project_brief"
    requirement = "requirement"
    user_story = "user_story"
    task = "task"
    test_case = "test_case"
    change_request = "change_request"


class ArtifactStatus(StrEnum):
    # Generic / requirement lifecycle.
    draft = "draft"
    reviewed = "reviewed"
    approved = "approved"
    changed = "changed"
    active = "active"
    archived = "archived"
    # ChangeRequest lifecycle.
    proposed = "proposed"
    in_review = "in_review"
    rejected = "rejected"
    applied = "applied"


class LinkType(StrEnum):
    refines = "refines"
    implements = "implements"
    tests = "tests"
    changes = "changes"
    depends_on = "depends_on"
    derived_from = "derived_from"
    related_to = "related_to"


class ChangeAction(StrEnum):
    created = "created"
    updated = "updated"
    status_changed = "status_changed"
    version_created = "version_created"
    linked = "linked"
    unlinked = "unlinked"
