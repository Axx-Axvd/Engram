"""Workflow engine: orchestrates LLM generation + persistence into connected artifacts."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from functools import lru_cache

from sqlalchemy.orm import Session

from engram.enums import ArtifactStatus, ArtifactType, LinkType
from engram.llm import GenItem, get_llm_provider
from engram.models import Artifact, ArtifactLink
from engram.repositories import artifact_repo, item_repo
from engram.schemas.analysis import ImpactAnalysisCreate
from engram.schemas.artifact import (
    ArtifactCreate,
    ArtifactItem,
    ArtifactRead,
    ItemRef,
)
from engram.schemas.link import LinkCreate, LinkRead
from engram.schemas.workflow import (
    ChangeImpactResult,
    ChangeRequestInput,
    FormalizeRequest,
    FormalizeResult,
    ImpactedArtifact,
)
from engram.services import (
    analysis_service,
    artifact_service,
    link_service,
    project_service,
)


def _first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "Change request")


def _title(text: str, max_len: int = 200) -> str:
    """Clean artifact title for a change request — the full request text lives in
    the content.

    Never bake an ellipsis into the stored title: views with room (detail panel,
    document header, graph node) wrap it in full, and narrow list rows clip it with
    a CSS ellipsis on their own. A title that already *contains* "…" would show that
    literal character even where the whole title fits.
    """
    head = _first_line(text)
    if len(head) <= max_len:
        return head or "Change request"
    return head[:max_len].rsplit(" ", 1)[0].rstrip() or head[:max_len].rstrip()


def _summarize(text: str, max_len: int = 70) -> str:
    head = _first_line(text)
    if len(head) > max_len:
        head = head[:max_len].rstrip() + "…"
    return head or "Change request"


class WorkflowEngine(ABC):
    @abstractmethod
    def formalize(self, session: Session, request: FormalizeRequest) -> FormalizeResult:
        """Project description -> requirements -> user stories -> tasks -> test cases (+links)."""

    @abstractmethod
    def analyze_change(self, session: Session, request: ChangeRequestInput) -> ChangeImpactResult:
        """Change request -> impacted artifacts -> new versions + changes-links."""


class ProceduralWorkflowEngine(WorkflowEngine):
    def formalize(self, session: Session, request: FormalizeRequest) -> FormalizeResult:
        llm = get_llm_provider()
        project = llm.formalize_project(request.description)
        artifacts: list[Artifact] = []
        links: list[ArtifactLink] = []

        # The project brief is the shared source/root that every document derives from.
        brief = artifact_service.create_artifact(
            session,
            ArtifactCreate(
                project_id=request.project_id,
                type=ArtifactType.project_brief,
                title="Project brief",
                content=project.brief,
                status=ArtifactStatus.approved,
                source_ref="chat",
                created_by=request.created_by,
            ),
        )
        artifacts.append(brief)

        def _doc(
            type_: ArtifactType,
            title: str,
            gen_items: list[GenItem],
            ref_doc_id: uuid.UUID | None = None,
        ) -> Artifact:
            items = [
                ArtifactItem(
                    key=gen.key,
                    title=gen.title,
                    text=gen.text,
                    feature=gen.feature,
                    refs=(
                        [ItemRef(artifact_id=ref_doc_id, key=k) for k in gen.refs]
                        if ref_doc_id is not None
                        else []
                    ),
                )
                for gen in gen_items
            ]
            artifact = artifact_service.create_artifact(
                session,
                ArtifactCreate(
                    project_id=request.project_id,
                    type=type_,
                    title=title,
                    content=f"{len(items)} {title.lower()} grouped from the project brief.",
                    items=items,
                    source_ref=str(brief.id),
                    created_by=request.created_by,
                ),
            )
            artifacts.append(artifact)
            return artifact

        def _link(source: Artifact, target: Artifact, type_: LinkType) -> None:
            links.append(
                link_service.create_link(
                    session,
                    LinkCreate(
                        source_id=source.id,
                        target_id=target.id,
                        type=type_,
                        created_by=request.created_by,
                    ),
                )
            )

        # Requirements first so the other documents can reference its item keys.
        requirements = _doc(ArtifactType.requirement, "Requirements", project.requirements)
        stories = _doc(
            ArtifactType.user_story, "User stories", project.user_stories, requirements.id
        )
        tasks = _doc(ArtifactType.task, "Tasks", project.tasks, requirements.id)
        tests = _doc(ArtifactType.test_case, "Test cases", project.test_cases, requirements.id)

        for doc in (requirements, stories, tasks, tests):
            _link(doc, brief, LinkType.derived_from)
        _link(stories, requirements, LinkType.refines)
        _link(tasks, requirements, LinkType.implements)
        _link(tests, requirements, LinkType.tests)

        return FormalizeResult(
            artifacts=[ArtifactRead.model_validate(a) for a in artifacts],
            links=[LinkRead.model_validate(link) for link in links],
        )

    def analyze_change(self, session: Session, request: ChangeRequestInput) -> ChangeImpactResult:
        project_id = project_service.resolve_project_id(session, request.project_id)
        analysis = analysis_service.create_analysis(
            session,
            project_id,
            ImpactAnalysisCreate(
                query=request.text,
                context_budget=4000,
                max_candidates=request.max_impacted,
                created_by=request.created_by,
            ),
        )
        change_request = artifact_service.create_artifact(
            session,
            ArtifactCreate(
                project_id=project_id,
                type=ArtifactType.change_request,
                title=_title(request.text),
                content=request.text,
                status=ArtifactStatus.in_review,
                source_ref="user",
                created_by=request.created_by,
            ),
        )
        impacted: list[ImpactedArtifact] = []
        seen_artifacts: set[uuid.UUID] = set()
        for candidate in analysis.candidates:
            item = item_repo.get(session, candidate.item_id, project_id)
            if item is None or item.artifact_id is None or item.artifact_id in seen_artifacts:
                continue
            target = artifact_repo.get(session, item.artifact_id, project_id)
            if target is None or target.type == ArtifactType.change_request:
                continue
            seen_artifacts.add(target.id)
            impacted.append(
                ImpactedArtifact(
                    artifact=ArtifactRead.model_validate(target), rationale=candidate.rationale
                )
            )
        return ChangeImpactResult(
            change_request=ArtifactRead.model_validate(change_request),
            summary=analysis.summary,
            impacted=impacted,
            links=[],
        )


@lru_cache(maxsize=1)
def get_workflow_engine() -> WorkflowEngine:
    return ProceduralWorkflowEngine()
