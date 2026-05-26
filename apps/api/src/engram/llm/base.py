"""Abstract LLM provider interface and the small DTO it produces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedArtifact:
    """A piece of generated content destined to become an artifact."""

    title: str
    content: str


class LLMProvider(ABC):
    @abstractmethod
    def generate_requirements(self, description: str) -> list[GeneratedArtifact]: ...

    @abstractmethod
    def generate_user_stories(self, requirement: GeneratedArtifact) -> list[GeneratedArtifact]: ...

    @abstractmethod
    def generate_tasks(self, user_story: GeneratedArtifact) -> list[GeneratedArtifact]: ...

    @abstractmethod
    def generate_test_cases(self, requirement: GeneratedArtifact) -> list[GeneratedArtifact]: ...
