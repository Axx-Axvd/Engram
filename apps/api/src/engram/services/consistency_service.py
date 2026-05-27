"""Consistency checks over the whole project memory.

Artifacts are documents whose ``items`` carry cross-references (``refs``). The checks operate at
item level: requirement coverage by tasks and tests, dangling references, user stories tracing to
requirements, and change requests touching something.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from engram.enums import ArtifactType, LinkType
from engram.models import Artifact
from engram.repositories import artifact_repo, link_repo
from engram.schemas.consistency import ConsistencyIssue, ConsistencyReport


def _items(artifact: Artifact) -> list[dict]:
    return artifact.items or []


def check_consistency(session: Session) -> ConsistencyReport:
    artifacts = artifact_repo.list_artifacts(session, limit=10_000)
    links = link_repo.list_all(session)
    by_id: dict[str, Artifact] = {str(a.id): a for a in artifacts}

    issues: list[ConsistencyIssue] = []

    # Collect, per referrer type, the (requirement_doc_id, key) targets that are referenced.
    task_refs: set[tuple[str, str]] = set()
    test_refs: set[tuple[str, str]] = set()

    for artifact in artifacts:
        for item in _items(artifact):
            for ref in item.get("refs", []):
                target_id = ref.get("artifact_id")
                target_key = ref.get("key")
                target = by_id.get(target_id)
                key_exists = target is not None and any(
                    it.get("key") == target_key for it in _items(target)
                )
                if not key_exists:
                    issues.append(
                        ConsistencyIssue(
                            severity="error",
                            code="dangling_reference",
                            message=(
                                f"{artifact.title} · {item.get('key')} references "
                                f"{target_key} which no longer exists"
                            ),
                            artifact_id=artifact.id,
                            artifact_title=artifact.title,
                            item_key=item.get("key"),
                        )
                    )
                if artifact.type == ArtifactType.task:
                    task_refs.add((target_id, target_key))
                elif artifact.type == ArtifactType.test_case:
                    test_refs.add((target_id, target_key))

    # Requirement items should be covered by at least one task and one test.
    for artifact in artifacts:
        if artifact.type != ArtifactType.requirement:
            continue
        for item in _items(artifact):
            target = (str(artifact.id), item.get("key"))
            if target not in task_refs:
                issues.append(
                    ConsistencyIssue(
                        severity="warning",
                        code="requirement_without_task",
                        message=f"Requirement {item.get('key')} has no linked task",
                        artifact_id=artifact.id,
                        artifact_title=artifact.title,
                        item_key=item.get("key"),
                    )
                )
            if target not in test_refs:
                issues.append(
                    ConsistencyIssue(
                        severity="warning",
                        code="requirement_without_test",
                        message=f"Requirement {item.get('key')} has no linked test",
                        artifact_id=artifact.id,
                        artifact_title=artifact.title,
                        item_key=item.get("key"),
                    )
                )

    # User story items should trace to a requirement.
    for artifact in artifacts:
        if artifact.type != ArtifactType.user_story:
            continue
        for item in _items(artifact):
            traces = any(
                (target := by_id.get(ref.get("artifact_id"))) is not None
                and target.type == ArtifactType.requirement
                for ref in item.get("refs", [])
            )
            if not traces:
                issues.append(
                    ConsistencyIssue(
                        severity="warning",
                        code="user_story_without_requirement",
                        message=f"User story {item.get('key')} is not linked to a requirement",
                        artifact_id=artifact.id,
                        artifact_title=artifact.title,
                        item_key=item.get("key"),
                    )
                )

    # A change request must touch at least one artifact (a `changes` link).
    changes_sources = {str(link.source_id) for link in links if link.type == LinkType.changes}
    for artifact in artifacts:
        if artifact.type == ArtifactType.change_request and str(artifact.id) not in changes_sources:
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="change_request_without_impact",
                    message=f"Change request '{artifact.title}' has no impacted artifact",
                    artifact_id=artifact.id,
                    artifact_title=artifact.title,
                )
            )

    errors = sum(1 for issue in issues if issue.severity == "error")
    warnings = len(issues) - errors
    return ConsistencyReport(
        ok=errors == 0,
        errors=errors,
        warnings=warnings,
        checked_artifacts=len(artifacts),
        issues=issues,
    )
