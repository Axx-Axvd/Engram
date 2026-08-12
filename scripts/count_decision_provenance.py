"""Count where the rationale of this project's decisions is recorded.

The counting rule is committed before the labels are written, so it cannot be adjusted
to suit a result. See ``research/DECISION_PROVENANCE.md`` for the registered method.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

AXES = ("conclusion_in", "rationale_in", "alternatives_in")
REPOSITORY_VALUES = frozenset({"code", "adr", "doc", "commit"})
ALL_VALUES = REPOSITORY_VALUES | {"transcript", "nowhere"}


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict) or "decisions" not in value:
        raise SystemExit(f"{path} must be a JSON object with a 'decisions' array")
    return value


def _validate(decisions: list[dict]) -> list[dict]:
    """Return the labelled decisions, refusing anything malformed or half-labelled."""
    labelled: list[dict] = []
    for decision in decisions:
        identifier = decision.get("id", "<no id>")
        filled = [axis for axis in AXES if decision.get(axis) is not None]
        if not filled:
            continue
        if len(filled) != len(AXES):
            raise SystemExit(f"{identifier}: axes partially labelled: {sorted(filled)}")
        if decision.get("transcript_available") is None:
            raise SystemExit(f"{identifier}: transcript_available is required once labelled")
        for axis in AXES:
            values = decision[axis]
            if not isinstance(values, list) or not values:
                raise SystemExit(f"{identifier}.{axis}: expected a non-empty array")
            unknown = sorted(set(values) - ALL_VALUES)
            if unknown:
                raise SystemExit(f"{identifier}.{axis}: unknown values {unknown}")
            if "nowhere" in values and len(values) > 1:
                raise SystemExit(f"{identifier}.{axis}: 'nowhere' is exclusive")
            evidence = decision.get("evidence", {}).get(axis, {})
            missing = [v for v in values if v != "nowhere" and not evidence.get(v)]
            if missing:
                raise SystemExit(f"{identifier}.{axis}: citation missing for {missing}")
            if values == ["nowhere"] and not decision.get("searched", {}).get(axis):
                raise SystemExit(f"{identifier}.{axis}: 'nowhere' requires recorded search terms")
        labelled.append(decision)
    return labelled


def _only_in_transcript(decision: dict) -> bool:
    """True when the reason or the rejected alternatives survive nowhere but a transcript."""
    for axis in ("rationale_in", "alternatives_in"):
        values = set(decision[axis])
        if "transcript" in values and not (values & REPOSITORY_VALUES):
            return True
    return False


def _share(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a (empty denominator)"
    return f"{numerator}/{denominator} = {numerator / denominator:.1%}"


def _axis_table(decisions: list[dict], axis: str) -> str:
    counts: Counter[str] = Counter()
    for decision in decisions:
        counts.update(decision[axis])
    total = len(decisions)
    rows = [f"  {axis}"]
    for value in sorted(ALL_VALUES):
        count = counts.get(value, 0)
        rows.append(f"    {value:<12} {count:>3}  {count / total:.0%}")
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="research/decision_provenance.json")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.30,
        help="registered kill criterion, applied to the conditional share",
    )
    args = parser.parse_args()

    payload = _load(args.path)
    decisions = payload["decisions"]
    labelled = _validate(decisions)
    if not labelled:
        raise SystemExit("No decision is labelled yet; nothing to count.")

    only = [d for d in labelled if _only_in_transcript(d)]
    available = [d for d in labelled if d["transcript_available"]]
    only_available = [d for d in only if d["transcript_available"]]
    reachable = [d for d in only if "claude_code" in (d.get("transcript_store") or [])]

    print(f"population frozen at {payload.get('frozen_at')}")
    print(f"decisions in population: {len(decisions)}   labelled: {len(labelled)}")
    missing = len(labelled) - len(available)
    print(f"transcript available:    {len(available)}   unavailable: {missing}")
    print()
    print("rationale or rejected alternatives recorded ONLY in a transcript")
    print(f"  primary   (conditional):  {_share(len(only_available), len(available))}")
    print(f"  secondary (unconditional):{_share(len(only), len(labelled))}")
    print(f"  reachable by the importer:{_share(len(reachable), len(only))}  (Claude Code format)")
    print()
    for axis in AXES:
        print(_axis_table(labelled, axis))
    print()

    by_period: Counter[str] = Counter()
    only_by_period: Counter[str] = Counter()
    for decision in labelled:
        period = min(decision.get("dates") or ["unknown"])
        by_period[period[:7]] += 1
        if _only_in_transcript(decision):
            only_by_period[period[:7]] += 1
    print("by month of first appearance")
    for period in sorted(by_period):
        share = f"{only_by_period[period]:>2}/{by_period[period]:<2}"
        print(f"  {period}  {share} only in a transcript")
    print()

    if len(available) == 0:
        raise SystemExit("Conditional share undefined: no decision has a surviving transcript.")
    share = len(only_available) / len(available)
    verdict = "NOT REFUTED" if share >= args.threshold else "REFUTED"
    print(f"registered threshold {args.threshold:.0%} on the conditional share -> {verdict}")
    named = ", ".join(decision["id"] for decision in only) if only else "none"
    print(f"only-in-transcript: {named}")


if __name__ == "__main__":
    main()
