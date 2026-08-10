"""Score full, vector, graph and combined retrieval exports against a path-level gold set."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise SystemExit(f"{path} must contain a JSON array")
    return value


def _score(gold_rows: list[dict], result_rows: list[dict]) -> dict[str, dict]:
    gold = {row["id"]: set(row["relevant_paths"]) for row in gold_rows}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in result_rows:
        if row.get("case_id") not in gold:
            raise SystemExit(f"Unknown benchmark case: {row.get('case_id')}")
        grouped[str(row.get("variant"))].append(row)

    report: dict[str, dict] = {}
    for variant, rows in sorted(grouped.items()):
        true_positive = false_positive = false_negative = 0
        tokens = elapsed = 0.0
        digests: dict[str, set[str]] = defaultdict(set)
        runs_per_case: dict[str, int] = defaultdict(int)
        scored: set[str] = set()
        for row in rows:
            case_id = row["case_id"]
            runs_per_case[case_id] += 1
            if row.get("snapshot_digest"):
                digests[case_id].add(str(row["snapshot_digest"]))
            tokens += float(row.get("token_estimate", 0))
            elapsed += float(row.get("elapsed_ms", 0))
            # Repeated runs of the same case exist to test reproducibility; scoring them
            # again would only multiply the absolute counts.
            if case_id in scored:
                continue
            scored.add(case_id)
            actual = set(row.get("retrieved_paths", []))
            expected = gold[case_id]
            true_positive += len(actual & expected)
            false_positive += len(actual - expected)
            false_negative += len(expected - actual)
        precision = true_positive / max(1, true_positive + false_positive)
        recall = true_positive / max(1, true_positive + false_negative)
        f1 = 2 * precision * recall / max(1e-12, precision + recall)
        report[variant] = {
            "cases": len(scored),
            "runs": len(rows),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "false_warnings": false_positive,
            "average_tokens": round(tokens / max(1, len(rows)), 2),
            "average_elapsed_ms": round(elapsed / max(1, len(rows)), 2),
            # A case only tests reproducibility when it was actually run more than once.
            "repeated_cases": sum(1 for count in runs_per_case.values() if count > 1),
            "non_reproducible_cases": sum(
                1 for values in digests.values() if len(values) > 1
            ),
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gold", type=Path)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    print(json.dumps(_score(_load(args.gold), _load(args.results)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
