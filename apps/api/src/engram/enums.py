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


# Allowed statuses per artifact type. Mirrors the frontend `STATUSES_FOR_TYPE`
# (web/src/lib/types.ts) so the API rejects status/type combinations the UI never offers.
STATUSES_FOR_TYPE: dict[ArtifactType, frozenset[ArtifactStatus]] = {
    ArtifactType.project_brief: frozenset(
        {ArtifactStatus.draft, ArtifactStatus.approved, ArtifactStatus.archived}
    ),
    ArtifactType.requirement: frozenset(
        {
            ArtifactStatus.draft,
            ArtifactStatus.reviewed,
            ArtifactStatus.approved,
            ArtifactStatus.changed,
            ArtifactStatus.archived,
        }
    ),
    ArtifactType.user_story: frozenset(
        {ArtifactStatus.draft, ArtifactStatus.active, ArtifactStatus.archived}
    ),
    ArtifactType.task: frozenset(
        {ArtifactStatus.draft, ArtifactStatus.active, ArtifactStatus.archived}
    ),
    ArtifactType.test_case: frozenset(
        {ArtifactStatus.draft, ArtifactStatus.active, ArtifactStatus.archived}
    ),
    ArtifactType.change_request: frozenset(
        {
            ArtifactStatus.proposed,
            ArtifactStatus.in_review,
            ArtifactStatus.approved,
            ArtifactStatus.rejected,
            ArtifactStatus.applied,
        }
    ),
}


def status_allowed_for_type(artifact_type: ArtifactType, status: ArtifactStatus) -> bool:
    return status in STATUSES_FOR_TYPE.get(artifact_type, frozenset())


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
