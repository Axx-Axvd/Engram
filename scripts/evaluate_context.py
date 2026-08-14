"""Score the package and wide branches of the stage-10 comparison against the path-level gold set.

Absolute counters come from the first run of each case, so repeats cannot double them; repeats
exist to test reproducibility and are compared, not summed. Section 25.3 of the addendum.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def _load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _f1(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def score(gold_rows: list[dict], result_rows: list[dict]) -> dict[str, dict]:
    gold = {row["id"]: set(row["relevant_paths"]) for row in gold_rows}
    by_branch: dict[str, list[dict]] = defaultdict(list)
    for row in result_rows:
        if row["case_id"] not in gold:
            raise SystemExit(f"Unknown benchmark case: {row['case_id']}")
        by_branch[row["branch"]].append(row)

    report: dict[str, dict] = {}
    for branch, rows in sorted(by_branch.items()):
        true_positive = false_positive = false_negative = 0
        tokens = 0
        elapsed = 0.0
        errors = 0
        scored: set[str] = set()
        answers: dict[str, set[tuple[str, ...]]] = defaultdict(set)
        for row in sorted(rows, key=lambda value: (value["case_id"], value["repeat"])):
            answers[row["case_id"]].add(tuple(sorted(row["named_paths"])))
            if row.get("error"):
                errors += 1
            # Repeats test reproducibility; scoring them again would multiply absolute counts.
            if row["case_id"] in scored:
                continue
            scored.add(row["case_id"])
            expected = gold[row["case_id"]]
            named = set(row["named_paths"])
            true_positive += len(named & expected)
            false_positive += len(named - expected)
            false_negative += len(expected - named)
            tokens += row["context_tokens_estimate"]
            elapsed += row["elapsed_ms"]
        predicted = true_positive + false_positive
        expected_total = true_positive + false_negative
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / expected_total if expected_total else 0.0
        non_reproducible = sum(1 for variants in answers.values() if len(variants) > 1)
        report[branch] = {
            "cases": len(scored),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(_f1(precision, recall), 4),
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "avg_context_tokens": round(tokens / len(scored)) if scored else 0,
            "avg_elapsed_ms": round(elapsed / len(scored)) if scored else 0,
            "non_reproducible": f"{non_reproducible}/{len(answers)}",
            "model_errors": errors,
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gold", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("--threshold", type=float, default=0.02)
    args = parser.parse_args()

    report = score(_load(args.gold), _load(args.results))
    header = (
        f"{'branch':<9} {'prec':>6} {'recall':>7} {'F1':>7} {'TP':>4} {'FP':>4} "
        f"{'FN':>4} {'tokens':>8} {'ms':>7} {'repro':>7}"
    )
    print(header)
    print("-" * len(header))
    for branch, values in report.items():
        print(
            f"{branch:<9} {values['precision']:>6.3f} {values['recall']:>7.3f} "
            f"{values['f1']:>7.3f} {values['true_positive']:>4} "
            f"{values['false_positive']:>4} {values['false_negative']:>4} "
            f"{values['avg_context_tokens']:>8} {values['avg_elapsed_ms']:>7} "
            f"{values['non_reproducible']:>7}"
        )

    if {"package", "wide"} <= report.keys():
        gap = report["wide"]["f1"] - report["package"]["f1"]
        package_tokens = max(1, report["package"]["avg_context_tokens"])
        ratio = report["wide"]["avg_context_tokens"] / package_tokens
        print(f"\nwide - package F1 gap: {gap:+.4f}   context ratio: {ratio:.1f}x")
        if gap > args.threshold:
            verdict = "REFUTED - the wide branch wins beyond the registered margin"
        elif abs(gap) <= args.threshold:
            verdict = "PARITY within the margin - Engram spends less, it does not know more"
        else:
            verdict = "the package leads beyond the registered margin"
        print(f"registered threshold {args.threshold:+.2f} F1 -> {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
