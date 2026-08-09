"""Run the four retrieval variants against an Engram project's imported benchmark source."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

VARIANTS = ("full", "vector", "graph", "combined")


def _request(url: str, *, body: dict | None = None):
    payload = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"Engram API returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cannot reach Engram API: {exc.reason}") from exc


def _locator_path(title: str) -> str:
    return title.split(" · ", 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--project", required=True, help="Imported project UUID")
    parser.add_argument(
        "--gold", type=Path, default=Path("research/benchmark_cases.json")
    )
    parser.add_argument("--output", type=Path, default=Path("research/results.json"))
    parser.add_argument("--budget", type=int, default=100_000)
    parser.add_argument("--max-candidates", type=int, default=100)
    args = parser.parse_args()

    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    base = args.api.rstrip("/")
    items = _request(f"{base}/api/projects/{args.project}/items")
    item_by_id = {item["id"]: item for item in items}
    results: list[dict] = []

    for case in gold:
        for variant in VARIANTS:
            started = time.perf_counter()
            analysis = _request(
                f"{base}/api/projects/{args.project}/impact-analyses",
                body={
                    "query": case["change"],
                    "source_revision_id": None,
                    "context_budget": args.budget,
                    "max_candidates": args.max_candidates,
                    "retrieval_mode": variant,
                    "created_by": "retrieval-experiment",
                },
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            candidates = analysis.get("candidates", [])
            retrieved_paths = sorted(
                {
                    _locator_path(item_by_id[candidate["item_id"]]["title"])
                    for candidate in candidates
                    if candidate["item_id"] in item_by_id
                }
            )
            token_estimate = sum(
                int(candidate.get("selection_reason", {}).get("token_estimate", 0))
                for candidate in candidates
            )
            snapshot = [
                {
                    "item_id": candidate["item_id"],
                    "item_version_id": candidate["item_version_id"],
                    "selection_reason": candidate.get("selection_reason", {}),
                }
                for candidate in candidates
            ]
            snapshot.sort(key=lambda value: value["item_id"])
            digest = hashlib.sha256(
                json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            results.append(
                {
                    "case_id": case["id"],
                    "variant": variant,
                    "retrieved_paths": retrieved_paths,
                    "token_estimate": token_estimate,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "snapshot_digest": digest,
                    "analysis_id": analysis["id"],
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} retrieval runs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
