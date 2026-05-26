"""Deterministic mock LLM: derives structured artifacts from input text via simple heuristics.

No model, no tokens, fully reproducible — ideal for development, demos, and stable tests.
"""

from __future__ import annotations

import re

from engram.llm.base import GeneratedArtifact, LLMProvider

_SENTENCE_SPLIT = re.compile(r"[.\n;!?]+")
_MAX_REQUIREMENTS = 6


def _statements(text: str) -> list[str]:
    return [chunk.strip() for chunk in _SENTENCE_SPLIT.split(text) if len(chunk.strip()) >= 8]


def _titleize(text: str, max_len: int = 70) -> str:
    head = text.strip().split(",")[0].strip()
    if len(head) > max_len:
        head = head[:max_len].rstrip() + "…"
    return head[0].upper() + head[1:] if head else "Untitled"


def _lower_first(text: str) -> str:
    return text[0].lower() + text[1:] if text else text


class MockLLMProvider(LLMProvider):
    def generate_requirements(self, description: str) -> list[GeneratedArtifact]:
        statements = _statements(description) or [description.strip() or "Project goal"]
        return [
            GeneratedArtifact(
                title=_titleize(statement),
                content=f"The system shall support: {statement.rstrip('.')}.",
            )
            for statement in statements[:_MAX_REQUIREMENTS]
        ]

    def generate_user_stories(self, requirement: GeneratedArtifact) -> list[GeneratedArtifact]:
        goal = _lower_first(requirement.title.rstrip("."))
        return [
            GeneratedArtifact(
                title=f"As a user, I want {goal}",
                content=f"As a user, I want {goal} so that I get the expected value.",
            )
        ]

    def generate_tasks(self, user_story: GeneratedArtifact) -> list[GeneratedArtifact]:
        subject = user_story.title
        return [
            GeneratedArtifact(
                title=f"Implement: {subject}",
                content=f"Implement backend and UI to fulfil '{subject}'.",
            ),
            GeneratedArtifact(
                title=f"Wire up tests: {subject}",
                content=f"Add automated coverage for '{subject}'.",
            ),
        ]

    def generate_test_cases(self, requirement: GeneratedArtifact) -> list[GeneratedArtifact]:
        subject = requirement.title.rstrip(".")
        return [
            GeneratedArtifact(
                title=f"Verify: {subject}",
                content=f"Given the system, when exercising '{subject}', it behaves as specified.",
            )
        ]
