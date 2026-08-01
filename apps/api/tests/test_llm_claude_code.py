"""Offline unit tests for the claude_code provider's pure parse/render helpers.

These never touch the Agent SDK (it's lazy-imported inside ``_ask``), so they run without the `llm`
extra installed and stay fully deterministic.
"""

from __future__ import annotations

import json

import pytest

from engram.llm.base import ContextItem
from engram.llm.claude_code import (
    _extract_json,
    _parse_change_analysis,
    _parse_formalized,
    _render_change_prompt,
)

_FORMALIZE = {
    "brief": "A todo app.",
    "requirements": [
        {
            "key": "R1",
            "title": "Create tasks",
            "text": "The system shall let users create tasks.",
            "feature": "Tasks",
        }
    ],
    "user_stories": [
        {
            "key": "US1",
            "title": "Create",
            "text": "As a user...",
            "feature": "Tasks",
            "refs": ["R1"],
        }
    ],
    "tasks": [],
    "test_cases": [],
}


def test_extract_json_plain() -> None:
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_strips_fences_and_prose() -> None:
    reply = 'Sure!\n```json\n{"a": 1, "b": [2, 3]}\n```\nDone.'
    assert _extract_json(reply) == {"a": 1, "b": [2, 3]}


def test_extract_json_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        _extract_json("no json here")


def test_parse_formalized_maps_items() -> None:
    project = _parse_formalized(_FORMALIZE, fallback_brief="fallback")
    assert project.brief == "A todo app."
    assert len(project.requirements) == 1
    assert project.requirements[0].key == "R1"
    assert project.requirements[0].feature == "Tasks"
    assert project.user_stories[0].refs == ["R1"]


def test_parse_formalized_uses_fallback_brief() -> None:
    project = _parse_formalized(dict(_FORMALIZE, brief=""), fallback_brief="fallback brief")
    assert project.brief == "fallback brief"


def test_parse_formalized_skips_items_missing_key_or_text() -> None:
    data = {
        "requirements": [
            {"key": "R1", "text": "valid"},
            {"key": "", "text": "no key"},
            {"key": "R3", "text": ""},
            {"title": "no key field"},
        ]
    }
    project = _parse_formalized(data, fallback_brief="b")
    assert [r.key for r in project.requirements] == ["R1"]


def test_parse_formalized_requires_requirements() -> None:
    with pytest.raises(ValueError):
        _parse_formalized({"requirements": []}, fallback_brief="b")


def test_parse_change_analysis_filters_unknown_ids_and_empty_content() -> None:
    data = {
        "summary": "Impacts one doc.",
        "proposals": [
            {"artifact_id": "id-1", "proposed_content": "new body", "rationale": "because"},
            {"artifact_id": "ghost", "proposed_content": "hallucinated", "rationale": "x"},
            {"artifact_id": "id-1", "proposed_content": "  ", "rationale": "empty"},
        ],
    }
    analysis = _parse_change_analysis(data, valid_ids={"id-1"})
    assert analysis.summary == "Impacts one doc."
    assert len(analysis.proposals) == 1
    assert analysis.proposals[0].artifact_id == "id-1"
    assert analysis.proposals[0].proposed_content == "new body"


def test_parse_change_analysis_defaults_summary() -> None:
    analysis = _parse_change_analysis({"proposals": []}, valid_ids=set())
    assert analysis.summary == "No summary provided."
    assert analysis.proposals == []


def test_render_change_prompt_includes_ids_and_plaintext() -> None:
    doc = json.dumps(
        {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Hello world"}]}
            ],
        }
    )
    context = [ContextItem(id="id-1", type="requirement", title="Reqs", content=doc)]
    prompt = _render_change_prompt("Add dark mode", context)
    assert "Add dark mode" in prompt
    assert "id-1" in prompt
    assert "Hello world" in prompt
    # Tiptap JSON is flattened to prose, not pasted raw.
    assert '"type": "doc"' not in prompt
