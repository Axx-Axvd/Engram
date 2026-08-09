"""Consistency checks over the whole project memory.

Artifacts are documents whose ``items`` carry cross-references (``refs``). The checks operate at
item level: requirement coverage by tasks and tests, dangling references, user stories tracing to
requirements, and change requests touching something.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from engram.enums import ArtifactStatus, ArtifactType, LinkState, LinkType
from engram.models import Artifact, ContextPackage, ImpactAnalysis, ImpactCandidate
from engram.repositories import artifact_repo, item_repo, link_repo
from engram.schemas.consistency import ConsistencyIssue, ConsistencyReport
from engram.services import project_service


def _items(artifact: Artifact) -> list[dict]:
    return artifact.items or []


def check_consistency(session: Session, project_id: uuid.UUID | None = None) -> ConsistencyReport:
    selected_project_id = project_service.resolve_project_id(session, project_id)
    artifacts = artifact_repo.list_artifacts(session, limit=10_000, project_id=selected_project_id)
    links = link_repo.list_all(session, selected_project_id)
    by_id: dict[str, Artifact] = {str(a.id): a for a in artifacts}

    # Document-level adjacency (undirected) from the Links graph, so checks can fall back to
    # hand-authored links when a document carries no items.
    linked_ids: dict[str, set[str]] = {}
    for link in links:
        s, t = str(link.source_id), str(link.target_id)
        linked_ids.setdefault(s, set()).add(t)
        linked_ids.setdefault(t, set()).add(s)

    def doc_links_to_type(artifact: Artifact, kind: ArtifactType) -> bool:
        return any(
            (other := by_id.get(other_id)) is not None and other.type == kind
            for other_id in linked_ids.get(str(artifact.id), ())
        )

    issues: list[ConsistencyIssue] = []

    knowledge_items = item_repo.list_items(session, selected_project_id, include_stale=True)
    for item in knowledge_items:
        if item.valid_to is not None:
            continue
        version = item_repo.current_version(session, item)
        if item.source_locator_id is None or version is None or version.source_locator_id is None:
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="active_item_without_provenance",
                    message=f"Active knowledge item {item.key} has no fixed source locator",
                    artifact_id=item.artifact_id,
                    item_key=item.key,
                )
            )
        elif not version.is_active:
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="inactive_current_item_version",
                    message=f"Knowledge item {item.key} points to an inactive current version",
                    artifact_id=item.artifact_id,
                    item_key=item.key,
                )
            )

    for link in item_repo.list_links(session, selected_project_id):
        if not link.evidence_locator_ids:
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="item_link_without_evidence",
                    message=f"Item link {link.id} has no source evidence",
                )
            )
        if link.state == LinkState.stale.value:
            issues.append(
                ConsistencyIssue(
                    severity="warning",
                    code="stale_item_link",
                    message=f"Item link {link.id} depends on an outdated item version",
                )
            )
        elif link.state == LinkState.proposed.value:
            issues.append(
                ConsistencyIssue(
                    severity="warning",
                    code="proposed_item_link",
                    message=f"Item link {link.id} still requires human review",
                )
            )

    packages = session.scalars(
        select(ContextPackage).where(ContextPackage.project_id == selected_project_id)
    )
    for package in packages:
        if package.token_estimate > package.token_budget:
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="context_package_over_budget",
                    message=f"Context Package {package.id} exceeds its hard token budget",
                )
            )

    analysis_ids = select(ImpactAnalysis.id).where(ImpactAnalysis.project_id == selected_project_id)
    candidates = session.scalars(
        select(ImpactCandidate).where(ImpactCandidate.analysis_id.in_(analysis_ids))
    )
    for candidate in candidates:
        if not candidate.evidence:
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="impact_candidate_without_evidence",
                    message=f"Impact candidate {candidate.id} has no evidence",
                )
            )

    # Collect, per referrer type, the (requirement_doc_id, key) targets that are referenced.
    task_refs: set[tuple[str, str]] = set()
    test_refs: set[tuple[str, str]] = set()
    story_refs: set[tuple[str, str]] = set()
    archived_flagged: set[tuple[str, str]] = set()

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
                elif artifact.type == ArtifactType.user_story:
                    story_refs.add((target_id, target_key))

                # A live document must not lean on an archived artifact as if current.
                if (
                    target is not None
                    and target.status == ArtifactStatus.archived
                    and artifact.status != ArtifactStatus.archived
                    and (str(artifact.id), target_id) not in archived_flagged
                ):
                    archived_flagged.add((str(artifact.id), target_id))
                    issues.append(
                        ConsistencyIssue(
                            severity="warning",
                            code="archived_used_as_active",
                            message=(
                                f"{artifact.title} references archived document '{target.title}'"
                            ),
                            artifact_id=artifact.id,
                            artifact_title=artifact.title,
                            item_key=item.get("key"),
                        )
                    )

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
            if target not in story_refs:
                issues.append(
                    ConsistencyIssue(
                        severity="warning",
                        code="requirement_without_user_story",
                        message=f"Requirement {item.get('key')} has no linked user story",
                        artifact_id=artifact.id,
                        artifact_title=artifact.title,
                        item_key=item.get("key"),
                    )
                )

    # An approved requirement document must record where it came from (spec §10.1.1).
    for artifact in artifacts:
        if (
            artifact.type == ArtifactType.requirement
            and artifact.status == ArtifactStatus.approved
            and not (artifact.source_ref and artifact.source_ref.strip())
        ):
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="approved_requirement_without_source",
                    message=f"Approved requirement '{artifact.title}' has no source",
                    artifact_id=artifact.id,
                    artifact_title=artifact.title,
                )
            )

    # User stories should trace to a requirement (spec §10.1.2). A document-level link to a
    # requirement satisfies the rule; otherwise each item must reference one. Hand-authored stories
    # with no items are checked at the document level.
    for artifact in artifacts:
        if artifact.type != ArtifactType.user_story:
            continue
        doc_traces = doc_links_to_type(artifact, ArtifactType.requirement)
        items = _items(artifact)
        if not items:
            if not doc_traces:
                issues.append(
                    ConsistencyIssue(
                        severity="warning",
                        code="user_story_without_requirement",
                        message=f"User story '{artifact.title}' is not linked to a requirement",
                        artifact_id=artifact.id,
                        artifact_title=artifact.title,
                    )
                )
            continue
        for item in items:
            traces = doc_traces or any(
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

    # Only an approved/applied legacy change request must touch an artifact. New in-review
    # requests are represented by ImpactAnalysis candidates and are intentionally non-mutating.
    changes_sources = {str(link.source_id) for link in links if link.type == LinkType.changes}
    for artifact in artifacts:
        if (
            artifact.type == ArtifactType.change_request
            and artifact.status in (ArtifactStatus.approved, ArtifactStatus.applied)
            and str(artifact.id) not in changes_sources
        ):
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="change_request_without_impact",
                    message=f"Change request '{artifact.title}' has no impacted artifact",
                    artifact_id=artifact.id,
                    artifact_title=artifact.title,
                )
            )

    # An approved/applied change request must have produced a new version in at least one of
    # the artifacts it changes (spec §10.1.7). current_version > 1 means it was revised.
    changes_targets: dict[str, list[Artifact]] = {}
    for link in links:
        if link.type == LinkType.changes:
            target = by_id.get(str(link.target_id))
            if target is not None:
                changes_targets.setdefault(str(link.source_id), []).append(target)

    for artifact in artifacts:
        if artifact.type != ArtifactType.change_request:
            continue
        if artifact.status not in (ArtifactStatus.approved, ArtifactStatus.applied):
            continue
        targets = changes_targets.get(str(artifact.id), [])
        if targets and not any(target.current_version > 1 for target in targets):
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="approved_cr_without_new_version",
                    message=(
                        f"Approved change request '{artifact.title}' produced no new version "
                        "in any linked artifact"
                    ),
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
