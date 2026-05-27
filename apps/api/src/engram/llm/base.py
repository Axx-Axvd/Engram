"""Abstract LLM provider interface and the small DTOs it produces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedArtifact:
    """A piece of generated content destined to become an artifact."""

    title: str
    content: str


@dataclass(frozen=True)
class ContextItem:
    """An existing artifact handed to the model as change-analysis context."""

    id: str
    type: str
    title: str
    content: str


@dataclass(frozen=True)
class ChangeProposal:
    """A proposed revision to one artifact in response to a change request."""

    artifact_id: str
    proposed_content: str
    rationale: str


@dataclass(frozen=True)
class ChangeAnalysis:
    summary: str
    proposals: list[ChangeProposal]


class LLMProvider(ABC):
    @abstractmethod
    def generate_requirements(self, description: str) -> list[GeneratedArtifact]: ...

    @abstractmethod
    def generate_user_stories(self, requirement: GeneratedArtifact) -> list[GeneratedArtifact]: ...

    @abstractmethod
    def generate_tasks(self, user_story: GeneratedArtifact) -> list[GeneratedArtifact]: ...

    @abstractmethod
    def generate_test_cases(self, requirement: GeneratedArtifact) -> list[GeneratedArtifact]: ...

    @abstractmethod
    def analyze_change_request(
        self, change_text: str, context: list[ContextItem]
    ) -> ChangeAnalysis: ...
