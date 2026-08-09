"""Abstract LLM provider interface and the DTOs it produces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenItem:
    """A generated document item. ``refs`` are item keys in the requirements document."""

    key: str
    title: str
    text: str
    feature: str | None = None
    refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FormalizedProject:
    """A whole formalization grouped into one document's worth of items per type."""

    brief: str
    requirements: list[GenItem]
    user_stories: list[GenItem]
    tasks: list[GenItem]
    test_cases: list[GenItem]


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


@dataclass(frozen=True)
class ContextElement:
    """An exact item version with provenance and its context-selection evidence."""

    id: str
    item_version_id: str
    type: str
    key: str
    title: str
    text: str
    status: str
    source_locator: dict | None
    links: list[dict] = field(default_factory=list)
    selection_reason: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ImpactProposal:
    item_id: str
    item_version_id: str
    impact_type: str
    confidence: float
    rationale: str
    evidence: list[str]
    proposed_action: str


@dataclass(frozen=True)
class ImpactAnalysisResult:
    summary: str
    proposals: list[ImpactProposal]


class LLMProvider(ABC):
    @abstractmethod
    def formalize_project(self, description: str) -> FormalizedProject:
        """Turn a free-text description into grouped requirements/stories/tasks/test-case items."""

    @abstractmethod
    def analyze_change_request(
        self, change_text: str, context: list[ContextItem]
    ) -> ChangeAnalysis: ...

    @abstractmethod
    def analyze_impact(
        self, change_text: str, context: list[ContextElement]
    ) -> ImpactAnalysisResult:
        """Classify evidence-backed impact without mutating project knowledge."""
