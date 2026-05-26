"""Workflow engine: orchestrates LLM generation + persistence into connected artifacts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from sqlalchemy.orm import Session

from engram.enums import ArtifactType, LinkType
from engram.llm import GeneratedArtifact, get_llm_provider
from engram.models import Artifact, ArtifactLink
from engram.schemas.artifact import ArtifactCreate, ArtifactRead
from engram.schemas.link import LinkCreate, LinkRead
from engram.schemas.workflow import FormalizeRequest, FormalizeResult
from engram.services import artifact_service, link_service


class WorkflowEngine(ABC):
    @abstractmethod
    def formalize(self, session: Session, request: FormalizeRequest) -> FormalizeResult:
        """Project description -> requirements -> user stories -> tasks -> test cases (+links)."""


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


@lru_cache(maxsize=1)
def get_workflow_engine() -> WorkflowEngine:
    return ProceduralWorkflowEngine()
