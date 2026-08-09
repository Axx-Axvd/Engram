"""Safe impact analysis, human review and reproducible context packages."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from engram.config import settings
from engram.enums import AnalysisStatus, ImpactType, ReviewDecision
from engram.errors import NotFoundError, ValidationError
from engram.llm import ContextElement, get_llm_provider
from engram.models import (
    ChangeSet,
    ChangeSetItem,
    ContextPackage,
    ContextPackageItem,
    EvidenceRef,
    ImpactAnalysis,
    ImpactCandidate,
    ItemVersion,
)
from engram.repositories import analysis_repo, item_repo, source_repo
from engram.schemas.analysis import (
    CandidateReview,
    ChangeSetItemRead,
    ChangeSetRead,
    ContextPackageItemRead,
    ContextPackageRead,
    ImpactAnalysisCreate,
    ImpactAnalysisRead,
    ImpactCandidateRead,
)
from engram.schemas.item import ItemRead, ItemVersionRead
from engram.schemas.source import SourceLocatorRead
from engram.services import context_service, project_service


def _context_element(selected: context_service.SelectedElement) -> ContextElement:
    locator = None
    if selected.locator is not None:
        locator = {
            "id": str(selected.locator.id),
            "source_revision_id": str(selected.locator.source_revision_id),
            "kind": selected.locator.kind,
            "path": selected.locator.path,
            "start_line": selected.locator.start_line,
            "end_line": selected.locator.end_line,
            "url": selected.locator.url,
            "external_id": selected.locator.external_id,
            "content_hash": selected.locator.content_hash,
        }
    return ContextElement(
        id=str(selected.item.id),
        item_version_id=str(selected.version.id),
        type=selected.item.type,
        key=selected.item.key,
        title=selected.version.title,
        text=selected.version.text,
        status=selected.version.status,
        source_locator=locator,
        links=selected.graph_path,
        selection_reason={
            **selected.reason,
            "score": selected.score,
            "token_estimate": selected.token_estimate,
        },
    )


def _analysis_read(session: Session, analysis: ImpactAnalysis) -> ImpactAnalysisRead:
    candidates = analysis_repo.list_candidates(session, analysis.id)
    return ImpactAnalysisRead(
        **{
            column: getattr(analysis, column)
            for column in (
                "id",
                "project_id",
                "source_revision_id",
                "request_text",
                "status",
                "summary",
                "model_provider",
                "model_name",
                "algorithm_version",
                "retrieval_mode",
                "context_budget",
                "created_at",
                "created_by",
            )
        },
        candidates=[ImpactCandidateRead.model_validate(candidate) for candidate in candidates],
    )


def create_analysis(
    session: Session,
    project_id: uuid.UUID,
    data: ImpactAnalysisCreate,
) -> ImpactAnalysisRead:
    project_service.get_project(session, project_id)
    if (
        data.source_revision_id is not None
        and source_repo.get_revision(session, project_id, data.source_revision_id) is None
    ):
        raise ValidationError("Source revision does not belong to the selected project")

    selected = context_service.select_context_elements(
        session,
        project_id=project_id,
        query=data.query,
        limit=data.max_candidates,
        hops=2,
        token_budget=data.context_budget,
        retrieval_mode=data.retrieval_mode.value,
    )
    context = [_context_element(element) for element in selected]
    try:
        result = get_llm_provider().analyze_impact(data.query, context)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Impact model returned invalid structured output") from exc
    selected_by_id = {str(element.item.id): element for element in selected}
    proposal_ids = [proposal.item_id for proposal in result.proposals]
    if len(proposal_ids) != len(set(proposal_ids)):
        raise ValidationError("Impact analysis returned duplicate items")
    if any(item_id not in selected_by_id for item_id in proposal_ids):
        raise ValidationError("Impact analysis returned an item outside its context")
    valid_impact_types = {value.value for value in ImpactType}
    for proposal in result.proposals:
        selected_element = selected_by_id[proposal.item_id]
        if str(selected_element.version.id) != proposal.item_version_id:
            raise ValidationError("Impact analysis referenced a stale item version")
        if proposal.impact_type not in valid_impact_types:
            raise ValidationError("Impact analysis returned an invalid impact type")
        if not 0 <= proposal.confidence <= 1:
            raise ValidationError("Impact analysis confidence must be between zero and one")
        if not proposal.rationale.strip() or not proposal.proposed_action.strip():
            raise ValidationError("Impact analysis requires a rationale and proposed review action")
        expected_evidence = (
            str(selected_element.locator.id)
            if selected_element.locator is not None
            else f"item-version:{selected_element.version.id}"
        )
        if not proposal.evidence or any(value != expected_evidence for value in proposal.evidence):
            raise ValidationError("Impact analysis returned evidence outside its context")

    analysis = analysis_repo.add(
        session,
        ImpactAnalysis(
            project_id=project_id,
            source_revision_id=data.source_revision_id,
            request_text=data.query,
            status=AnalysisStatus.in_review.value,
            summary=result.summary,
            model_provider=settings.llm_provider,
            model_name=settings.llm_model,
            algorithm_version=f"impact-v1:{data.retrieval_mode.value}",
            retrieval_mode=data.retrieval_mode.value,
            context_budget=data.context_budget,
            created_by=data.created_by,
        ),
    )
    for proposal in result.proposals:
        selected_element = selected_by_id[proposal.item_id]
        candidate = analysis_repo.add(
            session,
            ImpactCandidate(
                analysis_id=analysis.id,
                item_id=selected_element.item.id,
                item_version_id=selected_element.version.id,
                impact_type=proposal.impact_type,
                confidence=proposal.confidence,
                rationale=proposal.rationale,
                proposed_action=proposal.proposed_action,
                evidence=proposal.evidence,
                selection_reason={
                    **selected_element.reason,
                    "score": selected_element.score,
                    "graph_path": selected_element.graph_path,
                    "token_estimate": selected_element.token_estimate,
                },
                decision=ReviewDecision.pending.value,
            ),
        )
        if selected_element.locator is not None:
            session.add(
                EvidenceRef(
                    project_id=project_id,
                    source_locator_id=selected_element.locator.id,
                    subject_type="impact_candidate",
                    subject_id=candidate.id,
                    excerpt=selected_element.version.text[:1000],
                    digest=hashlib.sha256(proposal.rationale.encode()).hexdigest(),
                )
            )
    session.flush()
    return _analysis_read(session, analysis)


def get_analysis(
    session: Session, project_id: uuid.UUID, analysis_id: uuid.UUID
) -> ImpactAnalysisRead:
    analysis = analysis_repo.get_analysis(session, project_id, analysis_id)
    if analysis is None:
        raise NotFoundError(f"Impact analysis {analysis_id} not found")
    return _analysis_read(session, analysis)


def list_analyses(session: Session, project_id: uuid.UUID) -> list[ImpactAnalysisRead]:
    project_service.get_project(session, project_id)
    return [
        _analysis_read(session, analysis)
        for analysis in analysis_repo.list_analyses(session, project_id)
    ]


def review_candidate(
    session: Session,
    project_id: uuid.UUID,
    analysis_id: uuid.UUID,
    candidate_id: uuid.UUID,
    data: CandidateReview,
) -> ImpactCandidateRead:
    analysis = analysis_repo.get_analysis(session, project_id, analysis_id)
    if analysis is None:
        raise NotFoundError(f"Impact analysis {analysis_id} not found")
    candidate = analysis_repo.get_candidate(session, analysis_id, candidate_id)
    if candidate is None:
        raise NotFoundError(f"Impact candidate {candidate_id} not found")
    candidate.decision = data.decision.value
    candidate.reviewed_by = data.reviewed_by
    candidate.reviewed_at = datetime.now(UTC)
    decisions = [value.decision for value in analysis_repo.list_candidates(session, analysis.id)]
    if decisions and all(value == ReviewDecision.rejected.value for value in decisions):
        analysis.status = AnalysisStatus.rejected.value
    elif decisions and all(value != ReviewDecision.pending.value for value in decisions):
        analysis.status = AnalysisStatus.approved.value
    else:
        analysis.status = AnalysisStatus.in_review.value
    session.flush()
    return ImpactCandidateRead.model_validate(candidate)


def build_context_package(
    session: Session,
    project_id: uuid.UUID,
    analysis_id: uuid.UUID,
    *,
    token_budget: int,
    created_by: str,
) -> ContextPackageRead:
    analysis = analysis_repo.get_analysis(session, project_id, analysis_id)
    if analysis is None:
        raise NotFoundError(f"Impact analysis {analysis_id} not found")
    candidates = [
        candidate
        for candidate in analysis_repo.list_candidates(session, analysis_id)
        if candidate.decision == ReviewDecision.approved.value
    ]
    if not candidates:
        raise ValidationError("Approve at least one impact candidate before building context")
    package = analysis_repo.add(
        session,
        ContextPackage(
            project_id=project_id,
            analysis_id=analysis_id,
            token_budget=token_budget,
            token_estimate=0,
            created_by=created_by,
        ),
    )
    used = 0
    rank = 1
    for candidate in sorted(candidates, key=lambda value: value.confidence, reverse=True):
        item = item_repo.get(session, candidate.item_id, project_id)
        version = session.get(ItemVersion, candidate.item_version_id)
        if item is None or version is None:
            raise ValidationError("Approved candidate references missing knowledge")
        tokens = context_service.estimate_tokens(version.title, version.text)
        if used + tokens > token_budget:
            continue
        analysis_repo.add(
            session,
            ContextPackageItem(
                package_id=package.id,
                item_id=item.id,
                item_version_id=version.id,
                rank=rank,
                score=candidate.confidence,
                token_estimate=tokens,
                reason={
                    "impact_type": candidate.impact_type,
                    "rationale": candidate.rationale,
                    "evidence": candidate.evidence,
                    "selection": candidate.selection_reason,
                },
                graph_path=candidate.selection_reason.get("graph_path", []),
            ),
        )
        rank += 1
        used += tokens
    if used == 0:
        raise ValidationError("No approved item fits inside the requested token budget")
    package.token_estimate = used
    session.flush()
    return get_context_package(session, project_id, package.id)


def get_context_package(
    session: Session, project_id: uuid.UUID, package_id: uuid.UUID
) -> ContextPackageRead:
    package = analysis_repo.get_package(session, project_id, package_id)
    if package is None:
        raise NotFoundError(f"Context package {package_id} not found")
    rows = session.scalars(
        select(ContextPackageItem)
        .where(ContextPackageItem.package_id == package.id)
        .order_by(ContextPackageItem.rank)
    )
    items: list[ContextPackageItemRead] = []
    for row in rows:
        item = item_repo.get(session, row.item_id, project_id)
        version = session.get(ItemVersion, row.item_version_id)
        if item is None or version is None:
            continue
        locator = (
            source_repo.get_locator(session, version.source_locator_id)
            if version.source_locator_id is not None
            else None
        )
        items.append(
            ContextPackageItemRead(
                item=ItemRead.model_validate(item),
                version=ItemVersionRead.model_validate(version),
                source_locator=(
                    SourceLocatorRead.model_validate(locator) if locator is not None else None
                ),
                rank=row.rank,
                score=row.score,
                token_estimate=row.token_estimate,
                reason=row.reason,
                graph_path=row.graph_path,
            )
        )
    return ContextPackageRead(
        id=package.id,
        project_id=package.project_id,
        analysis_id=package.analysis_id,
        token_budget=package.token_budget,
        token_estimate=package.token_estimate,
        created_at=package.created_at,
        created_by=package.created_by,
        items=items,
    )


def list_context_packages(session: Session, project_id: uuid.UUID) -> list[ContextPackageRead]:
    project_service.get_project(session, project_id)
    return [
        get_context_package(session, project_id, package.id)
        for package in analysis_repo.list_packages(session, project_id)
    ]


def _change_set_read(session: Session, change_set: ChangeSet) -> ChangeSetRead:
    items = list(
        session.scalars(
            select(ChangeSetItem)
            .where(ChangeSetItem.change_set_id == change_set.id)
            .order_by(ChangeSetItem.id)
        )
    )
    return ChangeSetRead(
        **{
            column: getattr(change_set, column)
            for column in (
                "id",
                "project_id",
                "analysis_id",
                "source_revision_id",
                "external_id",
                "external_url",
                "status",
                "summary",
                "created_at",
            )
        },
        items=[ChangeSetItemRead.model_validate(item) for item in items],
    )


def list_change_sets(session: Session, project_id: uuid.UUID) -> list[ChangeSetRead]:
    project_service.get_project(session, project_id)
    return [
        _change_set_read(session, change_set)
        for change_set in analysis_repo.list_change_sets(session, project_id)
    ]


def get_change_set(
    session: Session, project_id: uuid.UUID, change_set_id: uuid.UUID
) -> ChangeSetRead:
    change_set = analysis_repo.get_change_set(session, project_id, change_set_id)
    if change_set is None:
        raise NotFoundError(f"ChangeSet {change_set_id} not found")
    return _change_set_read(session, change_set)
