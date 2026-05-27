"""Workflow engine: orchestrates LLM generation + persistence into connected artifacts."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from functools import lru_cache

from sqlalchemy.orm import Session

from engram.enums import ArtifactStatus, ArtifactType, LinkType
from engram.llm import ContextItem, GenItem, get_llm_provider
from engram.models import Artifact, ArtifactLink
from engram.repositories import artifact_repo
from engram.schemas.artifact import (
    ArtifactCreate,
    ArtifactItem,
    ArtifactRead,
    ArtifactUpdate,
    ItemRef,
)
from engram.schemas.link import LinkCreate, LinkRead
from engram.schemas.search import ContextQuery
from engram.schemas.workflow import (
    ChangeImpactResult,
    ChangeRequestInput,
    FormalizeRequest,
    FormalizeResult,
    ImpactedArtifact,
)
from engram.services import artifact_service, context_service, link_service


def _summarize(text: str, max_len: int = 70) -> str:
    head = next((line.strip() for line in text.splitlines() if line.strip()), "Change request")
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
        llm = get_llm_provider()

        change_request = artifact_service.create_artifact(
            session,
            ArtifactCreate(
                type=ArtifactType.change_request,
                title=_summarize(request.text),
                content=request.text,
                status=ArtifactStatus.proposed,
                source_ref="user",
                created_by=request.created_by,
            ),
        )

        # Pull the minimal relevant slice of memory, then drop the CR itself and other CRs.
        bundle = context_service.select_context(
            session,
            ContextQuery(query=request.text, limit=request.max_impacted, hops=1),
        )
        candidates = [
            a
            for a in bundle.artifacts
            if a.id != change_request.id
            and a.type not in (ArtifactType.change_request, ArtifactType.project_brief)
        ]

        analysis = llm.analyze_change_request(
            request.text,
            [
                ContextItem(id=str(a.id), type=a.type.value, title=a.title, content=a.content)
                for a in candidates
            ],
        )

        impacted: list[ImpactedArtifact] = []
        links: list[ArtifactLink] = []
        for proposal in analysis.proposals:
            target = artifact_repo.get(session, uuid.UUID(proposal.artifact_id))
            if target is None:
                continue
            links.append(
                link_service.create_link(
                    session,
                    LinkCreate(
                        source_id=change_request.id,
                        target_id=target.id,
                        type=LinkType.changes,
                        created_by=request.created_by,
                    ),
                )
            )
            new_status = ArtifactStatus.changed if target.type == ArtifactType.requirement else None
            updated = artifact_service.update_artifact(
                session,
                target.id,
                ArtifactUpdate(
                    content=proposal.proposed_content,
                    status=new_status,
                    reason=f"change request: {_summarize(request.text)}",
                    updated_by=request.created_by,
                ),
            )
            impacted.append(
                ImpactedArtifact(
                    artifact=ArtifactRead.model_validate(updated), rationale=proposal.rationale
                )
            )

        # Record that the change request has been applied (creates its own new version).
        artifact_service.update_artifact(
            session,
            change_request.id,
            ArtifactUpdate(
                status=ArtifactStatus.applied, reason="applied", updated_by=request.created_by
            ),
        )
        change_request_fresh = artifact_repo.get(session, change_request.id)

        return ChangeImpactResult(
            change_request=ArtifactRead.model_validate(change_request_fresh),
            summary=analysis.summary,
            impacted=impacted,
            links=[LinkRead.model_validate(link) for link in links],
        )


@lru_cache(maxsize=1)
def get_workflow_engine() -> WorkflowEngine:
    return ProceduralWorkflowEngine()
