"""Workflow engine: orchestrates LLM generation + persistence into connected artifacts."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from functools import lru_cache

from sqlalchemy.orm import Session

from engram.enums import ArtifactStatus, ArtifactType, LinkType
from engram.llm import ContextItem, GeneratedArtifact, get_llm_provider
from engram.models import Artifact, ArtifactLink
from engram.repositories import artifact_repo
from engram.schemas.artifact import ArtifactCreate, ArtifactRead, ArtifactUpdate
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
        artifacts: list[Artifact] = []
        links: list[ArtifactLink] = []

        def _create(type_: ArtifactType, gen: GeneratedArtifact, source_ref: str) -> Artifact:
            artifact = artifact_service.create_artifact(
                session,
                ArtifactCreate(
                    type=type_,
                    title=gen.title,
                    content=gen.content,
                    source_ref=source_ref,
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

        for gen_req in llm.generate_requirements(request.description):
            requirement = _create(ArtifactType.requirement, gen_req, "project_description")

            for gen_tc in llm.generate_test_cases(gen_req):
                test_case = _create(ArtifactType.test_case, gen_tc, str(requirement.id))
                _link(test_case, requirement, LinkType.tests)

            for gen_story in llm.generate_user_stories(gen_req):
                story = _create(ArtifactType.user_story, gen_story, str(requirement.id))
                _link(story, requirement, LinkType.refines)

                for gen_task in llm.generate_tasks(gen_story):
                    task = _create(ArtifactType.task, gen_task, str(story.id))
                    _link(task, story, LinkType.implements)

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
            if a.id != change_request.id and a.type != ArtifactType.change_request
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
