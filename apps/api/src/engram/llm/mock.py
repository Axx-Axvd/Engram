"""Deterministic mock LLM: derives grouped, structured items from input text via simple heuristics.

No model, no tokens, fully reproducible — ideal for development, demos, and stable tests. The mock
packs everything into one document's worth of items per type (the engine creates the documents).
"""

from __future__ import annotations

import re

from engram.llm.base import (
    ChangeAnalysis,
    ChangeProposal,
    ContextItem,
    FormalizedProject,
    GenItem,
    LLMProvider,
)

_SENTENCE_SPLIT = re.compile(r"[.\n;!?]+")
_MAX_ITEMS = 10
_STOPWORDS = {
    "users",
    "user",
    "can",
    "the",
    "and",
    "with",
    "into",
    "their",
    "they",
    "that",
    "this",
    "have",
    "from",
    "when",
    "will",
    "shall",
    "able",
    "each",
    "also",
    "other",
    "than",
    "then",
    "them",
    "your",
    "should",
    "would",
    "could",
    "must",
    "want",
    "needs",
    "need",
}


def _statements(text: str) -> list[str]:
    return [chunk.strip() for chunk in _SENTENCE_SPLIT.split(text) if len(chunk.strip()) >= 8]


def _titleize(text: str, max_len: int = 70) -> str:
    head = text.strip().split(",")[0].strip()
    if len(head) > max_len:
        head = head[:max_len].rstrip() + "…"
    return head[0].upper() + head[1:] if head else "Untitled"


def _lower_first(text: str) -> str:
    return text[0].lower() + text[1:] if text else text


def _feature_label(text: str) -> str:
    """Crude feature/section label: the most salient (longest, non-stopword) token."""
    words = [w for w in re.findall(r"[A-Za-z]{4,}", text.lower()) if w not in _STOPWORDS]
    if not words:
        return "General"
    return max(words, key=len).capitalize()


class MockLLMProvider(LLMProvider):
    def formalize_project(self, description: str) -> FormalizedProject:
        statements = _statements(description) or [description.strip() or "Project goal"]
        statements = statements[:_MAX_ITEMS]

        requirements: list[GenItem] = []
        user_stories: list[GenItem] = []
        tasks: list[GenItem] = []
        test_cases: list[GenItem] = []

        for i, statement in enumerate(statements, start=1):
            feature = _feature_label(statement)
            rkey = f"R{i}"
            title = _titleize(statement)

            requirements.append(
                GenItem(
                    key=rkey,
                    title=title,
                    text=f"The system shall support: {statement.rstrip('.')}.",
                    feature=feature,
                )
            )
            user_stories.append(
                GenItem(
                    key=f"US{i}",
                    title=f"As a user, I want {_lower_first(title)}",
                    text=f"As a user, I want {_lower_first(title)} so that I get value.",
                    feature=feature,
                    refs=[rkey],
                )
            )
            tasks.append(
                GenItem(
                    key=f"T{i}",
                    title=f"Implement: {title}",
                    text=f"Implement backend and UI to fulfil '{title}'.",
                    feature=feature,
                    refs=[rkey],
                )
            )
            test_cases.append(
                GenItem(
                    key=f"TC{i}",
                    title=f"Verify: {title}",
                    text=f"Given the system, when exercising '{title}', it behaves as specified.",
                    feature=feature,
                    refs=[rkey],
                )
            )

        return FormalizedProject(
            brief=description.strip(),
            requirements=requirements,
            user_stories=user_stories,
            tasks=tasks,
            test_cases=test_cases,
        )

    def analyze_change_request(
        self, change_text: str, context: list[ContextItem]
    ) -> ChangeAnalysis:
        request = change_text.strip().rstrip(".")
        proposals = [
            ChangeProposal(
                artifact_id=item.id,
                proposed_content=f"{item.content}\n\n— Revised for change request: {request}.",
                rationale=f"'{item.title}' is in scope of the change and was updated accordingly.",
            )
            for item in context
        ]
        summary = (
            f"Change request '{request}' impacts {len(proposals)} document(s); "
            "each received a new version reflecting the change."
        )
        return ChangeAnalysis(summary=summary, proposals=proposals)
