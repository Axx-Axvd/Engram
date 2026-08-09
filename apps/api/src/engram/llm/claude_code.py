"""Real LLM provider backed by the Claude Agent SDK (subscription auth, no per-token API key).

Runs the locally installed, subscription-authenticated Claude CLI behind the same ``LLMProvider``
interface as the deterministic mock. Selected with ``ENGRAM_LLM_PROVIDER=claude_code``.

The Agent SDK is async and optional, so it's imported lazily — the default (mock) install stays
lean and offline. Each call is a single-shot, tools-disabled generation that must return exactly
one JSON object, which we parse into the same DTOs the mock produces. Output is non-deterministic
by nature: keep ``mock`` as the test/CI default.
"""

from __future__ import annotations

import asyncio
import json

from engram.config import settings
from engram.enums import ImpactType
from engram.llm.base import (
    ChangeAnalysis,
    ChangeProposal,
    ContextElement,
    ContextItem,
    FormalizedProject,
    GenItem,
    ImpactAnalysisResult,
    ImpactProposal,
    LLMProvider,
)
from engram.services.artifact_service import content_to_text

_MAX_ATTEMPTS = 3  # retry transient CLI / control-protocol errors before giving up

_FORMALIZE_SYSTEM = """\
You are a requirements analyst for Engram, a project-memory platform. Turn a free-text project \
description into connected, machine-readable artifacts.

Return ONLY a single JSON object (no markdown fences, no commentary) with exactly this shape:
{
  "brief": "<concise 1-3 sentence restatement of the project>",
  "requirements": [{"key": "R1", "title": "...", "text": "...", "feature": "..."}],
  "user_stories": [{"key": "US1", "title": "...", "text": "...", "feature": "...", "refs": ["R1"]}],
  "tasks": [{"key": "T1", "title": "...", "text": "...", "feature": "...", "refs": ["R1"]}],
  "test_cases": [{"key": "TC1", "title": "...", "text": "...", "feature": "...", "refs": ["R1"]}]
}

Rules:
- Keys are stable and sequential per list: R1.., US1.., T1.., TC1...
- Every item has a short "feature" label (a 1-2 word theme/area).
- Each user story, task, and test case references one or more requirement keys in "refs".
- "text" is a full sentence; requirements use "The system shall ..." phrasing.
- Cover the description with 1 to 10 items per list. Output valid JSON only."""

_CHANGE_SYSTEM = """\
You are a change-impact analyst for Engram, a project-memory platform. Given a change request and \
the existing project documents it might affect, decide which documents must change and how.

Return ONLY a single JSON object (no markdown fences, no commentary) with exactly this shape:
{
  "summary": "<1-2 sentence summary of the change and its impact>",
  "proposals": [
    {"artifact_id": "<id copied from the provided context>",
     "proposed_content": "<full revised document body, plain text>",
     "rationale": "<why this document changes>"}
  ]
}

Rules:
- Only propose changes to documents whose id appears in the provided context. Never invent ids.
- "proposed_content" is the FULL new body of the document as plain text (no JSON, no markdown).
- Include only documents that genuinely need to change; omit the rest.
- Output valid JSON only."""

_IMPACT_SYSTEM = """\
You are an evidence-constrained change-impact analyst. You receive exact, immutable knowledge-item \
versions selected from one project. Classify impact, but never rewrite or apply source data.

Return ONLY one JSON object with this shape:
{
  "summary": "...",
  "proposals": [
    {
      "item_id": "id copied from context",
      "item_version_id": "version id copied from context",
      "impact_type": "modify|verify|potentially_stale|no_change",
      "confidence": 0.0,
      "rationale": "why the evidence supports this classification",
      "evidence": ["source locator id copied from context"],
      "proposed_action": "a review action, not an applied edit"
    }
  ]
}

Rules:
- Never invent item ids, version ids or evidence ids.
- Every proposal must include at least one supplied evidence id and a non-empty rationale.
- Emit at most one proposal per item.
- Do not produce revised document text or claim that a change was applied.
- Output valid JSON only."""


def _extract_json(text: str) -> dict:
    """Slice the outermost ``{...}`` span out of a model reply and parse it.

    Tolerates markdown fences or stray prose around the object — we never trust the model to return
    a bare JSON document.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"LLM did not return a JSON object: {text[:200]!r}")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("LLM JSON root is not an object")
    return data


def _gen_items(raw: object) -> list[GenItem]:
    items: list[GenItem] = []
    if not isinstance(raw, list):
        return items
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key") or "").strip()
        body = str(entry.get("text") or "").strip()
        if not key or not body:
            continue
        feature = entry.get("feature")
        refs_raw = entry.get("refs")
        refs = (
            [str(r).strip() for r in refs_raw if str(r).strip()]
            if isinstance(refs_raw, list)
            else []
        )
        items.append(
            GenItem(
                key=key,
                title=str(entry.get("title") or key).strip(),
                text=body,
                feature=str(feature).strip() if feature else None,
                refs=refs,
            )
        )
    return items


def _parse_formalized(data: dict, fallback_brief: str) -> FormalizedProject:
    project = FormalizedProject(
        brief=str(data.get("brief") or "").strip() or fallback_brief,
        requirements=_gen_items(data.get("requirements")),
        user_stories=_gen_items(data.get("user_stories")),
        tasks=_gen_items(data.get("tasks")),
        test_cases=_gen_items(data.get("test_cases")),
    )
    if not project.requirements:
        raise ValueError("LLM formalization produced no requirements")
    return project


def _parse_change_analysis(data: dict, valid_ids: set[str]) -> ChangeAnalysis:
    proposals: list[ChangeProposal] = []
    raw = data.get("proposals")
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            artifact_id = str(entry.get("artifact_id") or "").strip()
            content = str(entry.get("proposed_content") or "").strip()
            if artifact_id not in valid_ids or not content:
                continue
            proposals.append(
                ChangeProposal(
                    artifact_id=artifact_id,
                    proposed_content=content,
                    rationale=str(entry.get("rationale") or "").strip(),
                )
            )
    summary = str(data.get("summary") or "").strip() or "No summary provided."
    return ChangeAnalysis(summary=summary, proposals=proposals)


def _parse_impact_analysis(
    data: dict,
    valid_versions: dict[str, str],
    valid_evidence: set[str],
) -> ImpactAnalysisResult:
    raw = data.get("proposals")
    if not isinstance(raw, list):
        raise ValueError("LLM impact analysis must contain a proposals array")
    proposals: list[ImpactProposal] = []
    seen: set[str] = set()
    allowed_types = {value.value for value in ImpactType}
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("Every impact proposal must be an object")
        item_id = str(entry.get("item_id") or "").strip()
        version_id = str(entry.get("item_version_id") or "").strip()
        impact_type = str(entry.get("impact_type") or "").strip()
        rationale = str(entry.get("rationale") or "").strip()
        proposed_action = str(entry.get("proposed_action") or "").strip()
        evidence_raw = entry.get("evidence")
        try:
            confidence = float(entry.get("confidence"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Impact confidence must be numeric") from exc
        if item_id not in valid_versions or valid_versions[item_id] != version_id:
            raise ValueError("LLM returned an unknown item or stale item version")
        if item_id in seen:
            raise ValueError("LLM returned duplicate impact proposals")
        if impact_type not in allowed_types:
            raise ValueError(f"Unknown impact type: {impact_type}")
        if not 0 <= confidence <= 1:
            raise ValueError("Impact confidence must be between 0 and 1")
        if not rationale or not proposed_action:
            raise ValueError("Impact proposal rationale and action are required")
        if not isinstance(evidence_raw, list) or not evidence_raw:
            raise ValueError("Every impact proposal requires evidence")
        evidence = [str(value) for value in evidence_raw]
        if any(value not in valid_evidence for value in evidence):
            raise ValueError("LLM returned evidence outside the supplied context")
        seen.add(item_id)
        proposals.append(
            ImpactProposal(
                item_id=item_id,
                item_version_id=version_id,
                impact_type=impact_type,
                confidence=confidence,
                rationale=rationale,
                evidence=evidence,
                proposed_action=proposed_action,
            )
        )
    return ImpactAnalysisResult(
        summary=str(data.get("summary") or "").strip() or "No impact summary provided.",
        proposals=proposals,
    )


def _render_change_prompt(change_text: str, context: list[ContextItem]) -> str:
    if context:
        blocks = "\n\n---\n\n".join(
            f"[{item.id}] ({item.type}) {item.title}\n{content_to_text(item.content).strip()}"
            for item in context
        )
    else:
        blocks = "(no existing documents)"
    return (
        f"Change request:\n\n{change_text.strip()}\n\n"
        f"Existing documents you may revise:\n\n{blocks}"
    )


def _render_impact_prompt(change_text: str, context: list[ContextElement]) -> str:
    payload = [
        {
            "item_id": element.id,
            "item_version_id": element.item_version_id,
            "type": element.type,
            "key": element.key,
            "title": element.title,
            "text": element.text,
            "status": element.status,
            "source_locator": element.source_locator,
            "links": element.links,
            "selection_reason": element.selection_reason,
        }
        for element in context
    ]
    return (
        f"Change request:\n\n{change_text.strip()}\n\n"
        f"Selected context elements:\n{json.dumps(payload, ensure_ascii=False)}"
    )


class ClaudeCodeLLMProvider(LLMProvider):
    """LLMProvider that delegates generation to the subscription-authenticated Claude CLI."""

    def formalize_project(self, description: str) -> FormalizedProject:
        description = description.strip()
        reply = self._ask(_FORMALIZE_SYSTEM, f"Project description:\n\n{description}")
        return _parse_formalized(_extract_json(reply), fallback_brief=description)

    def analyze_change_request(
        self, change_text: str, context: list[ContextItem]
    ) -> ChangeAnalysis:
        valid_ids = {item.id for item in context}
        reply = self._ask(_CHANGE_SYSTEM, _render_change_prompt(change_text, context))
        return _parse_change_analysis(_extract_json(reply), valid_ids)

    def analyze_impact(
        self, change_text: str, context: list[ContextElement]
    ) -> ImpactAnalysisResult:
        valid_versions = {element.id: element.item_version_id for element in context}
        valid_evidence = {
            str(element.source_locator["id"])
            if element.source_locator and element.source_locator.get("id")
            else f"item-version:{element.item_version_id}"
            for element in context
        }
        reply = self._ask(_IMPACT_SYSTEM, _render_impact_prompt(change_text, context))
        return _parse_impact_analysis(_extract_json(reply), valid_versions, valid_evidence)

    def _ask(self, system_prompt: str, user_prompt: str) -> str:
        """Run one tools-disabled query through the Agent SDK and return its text result.

        Bridges the async SDK into our synchronous service layer with ``asyncio.run`` — safe
        because the engine is always called from a worker thread (FastAPI sync route / pytest /
        scripts) with no running event loop.
        """
        try:
            from claude_agent_sdk import ClaudeAgentOptions, query
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError(
                "The 'claude_code' LLM provider needs claude-agent-sdk. Install it with: "
                "uv sync --extra llm  (and make sure the Claude CLI is logged in via your plan)."
            ) from exc

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=[],  # no tools auto-approved — this is pure single-shot generation
            setting_sources=[],  # skip repo/user CLAUDE.md / skills / settings in the prompt
            model=settings.llm_model,
            # max_turns is intentionally unset: with no tools the model always answers in one turn.
        )

        async def _run() -> str:
            final: str | None = None
            async for message in query(prompt=user_prompt, options=options):
                result = getattr(message, "result", None)
                if result:
                    final = result
            return final or ""

        # The CLI occasionally surfaces a transient control-protocol error on a cold or
        # rate-limited call (observed: "error result: success"); a few retries make it reliable.
        last_error: Exception | None = None
        for _ in range(_MAX_ATTEMPTS):
            try:
                reply = asyncio.run(_run())
            except Exception as exc:  # transient SDK/CLI failure — retry, then surface below
                last_error = exc
                continue
            if reply.strip():
                return reply
            last_error = RuntimeError("Claude Agent SDK returned an empty result.")
        raise RuntimeError(
            f"Claude Agent SDK call failed after {_MAX_ATTEMPTS} attempts: {last_error}"
        )
