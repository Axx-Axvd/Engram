"""Compare a bounded Engram package against a wide unselected dump, with one real model.

Stage 10 of ``ROADMAP.md``, registered as section 30.3 of the addendum with the amendment in
30.3.1. Both branches differ **only** in the context handed to the model: the prompt, the model,
the output contract and the scoring are identical. The wide branch carries the measured maximum
the channel accepts, holding every corpus file truncated proportionally so that no gold path is
invisible to it.

The Engram branch is built through the product's own retrieval, driven with the deterministic mock
provider so that the package is pure selection — exactly the artefact the earlier 23-case runs
measured. The real model is used only for the comparison task, in both branches alike.

Results are appended incrementally and completed rows are skipped, so an interrupted run resumes.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

BRANCHES = ("package", "wide")
IMPORT_SUFFIXES = (
    ".md", ".mdx", ".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".toml", ".yaml", ".yml", ".json",
)
MAX_FILE_BYTES = 250_000
MAX_ATTEMPTS = 3

SYSTEM_PROMPT = """\
You identify which files of a software repository a proposed change would affect.

Return ONLY a single JSON object, no markdown fences and no commentary, shaped exactly like this:
{"paths": ["apps/api/src/engram/models/item.py", "apps/api/tests/test_true_path.py"]}

Rules:
- Every path must be repository-relative and must appear in the context you were given.
- List only files a correct implementation of the change would have to create, edit or delete.
- Do not pad the list. Precision matters as much as recall.
- If the context does not let you decide, return the best-supported paths you can, never an
  explanation.
"""


def _request(url: str, *, body: dict | None = None, timeout: int = 300):
    payload = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"Engram API returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cannot reach Engram API: {exc.reason}") from exc


def _locator_path(title: str) -> str:
    return title.split(" · ", 1)[0]


def _write(output: Path, by_key: dict[tuple[str, str, int], dict]) -> None:
    rows = [by_key[key] for key in sorted(by_key)]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def estimate_tokens(text: str) -> int:
    """The estimator context_service uses, so both branches are counted the same way."""
    return max(1, math.ceil(len(text) / 4))


# --- the wide branch's corpus ------------------------------------------------------------------


def corpus_files(repo: Path, revision: str) -> list[tuple[str, str]]:
    listing = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--long", revision],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    files: list[tuple[str, str]] = []
    for line in listing.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        size, path = parts[3], parts[4]
        if not path.endswith(IMPORT_SUFFIXES) or not size.isdigit():
            continue
        if int(size) > MAX_FILE_BYTES:
            continue
        blob = subprocess.run(
            ["git", "-C", str(repo), "show", f"{revision}:{path}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout
        files.append((path, blob))
    return sorted(files)


def render_wide(files: list[tuple[str, str]], cap_chars: int) -> tuple[str, dict]:
    """Hold every file, truncating each in proportion so no path becomes invisible."""
    header_cost = sum(len(f"===== FILE: {path} =====\n\n\n") for path, _ in files)
    body_budget = max(0, cap_chars - header_cost)
    total_body = sum(len(body) for _, body in files)
    ratio = min(1.0, body_budget / total_body) if total_body else 1.0
    chunks = []
    kept = 0
    for path, body in files:
        take = len(body) if ratio >= 1.0 else int(len(body) * ratio)
        kept += take
        suffix = "" if take >= len(body) else f"\n[... {len(body) - take} characters omitted ...]"
        chunks.append(f"===== FILE: {path} =====\n{body[:take]}{suffix}")
    text = "\n\n".join(chunks)
    stats = {
        "files": len(files),
        "corpus_chars": total_body,
        "kept_chars": kept,
        "kept_fraction": round(kept / total_body, 4) if total_body else 1.0,
        "rendered_chars": len(text),
        "truncation_ratio": round(ratio, 4),
    }
    return text, stats


# --- the package branch ------------------------------------------------------------------------


def build_package(base: str, project: str, change: str, budget: int, max_candidates: int) -> dict:
    analysis = _request(
        f"{base}/api/projects/{project}/impact-analyses",
        body={
            "query": change,
            "source_revision_id": None,
            "context_budget": budget,
            "max_candidates": max_candidates,
            "retrieval_mode": "combined",
            "created_by": "context-experiment",
        },
    )
    return analysis


def render_package(analysis: dict, item_by_id: dict) -> tuple[str, dict]:
    chunks = []
    paths = set()
    for candidate in analysis.get("candidates", []):
        item = item_by_id.get(candidate["item_id"])
        if item is None:
            continue
        paths.add(_locator_path(item["title"]))
        chunks.append(f"===== FILE: {item['title']} =====\n{item['text']}")
    text = "\n\n".join(chunks)
    return text, {
        "elements": len(chunks),
        "distinct_paths": len(paths),
        "rendered_chars": len(text),
    }


# --- the model -----------------------------------------------------------------------------------


async def _ask(system: str, prompt: str, model: str | None) -> str:
    from claude_agent_sdk import ClaudeAgentOptions, query

    options = ClaudeAgentOptions(
        system_prompt=system, allowed_tools=[], setting_sources=[], model=model
    )
    final = None
    async for message in query(prompt=prompt, options=options):
        result = getattr(message, "result", None)
        if result:
            final = result
    return final or ""


def ask_model(context: str, change: str, model: str | None) -> tuple[list[str], str]:
    prompt = (
        f"{context}\n\n===== PROPOSED CHANGE =====\n{change}\n\n"
        'Which repository files would this change affect? Answer with the JSON object only.'
    )
    last = ""
    for _ in range(MAX_ATTEMPTS):
        try:
            reply = asyncio.run(_ask(SYSTEM_PROMPT, prompt, model))
        except Exception as exc:  # noqa: BLE001 - transient CLI failures are expected
            last = f"{type(exc).__name__}: {exc}"[:200]
            continue
        if not reply.strip():
            last = "empty result"
            continue
        try:
            start, end = reply.index("{"), reply.rindex("}")
            payload = json.loads(reply[start : end + 1])
            paths = [str(value) for value in payload.get("paths", [])]
            return sorted(set(paths)), ""
        except (ValueError, json.JSONDecodeError, AttributeError) as exc:
            last = f"unparsable reply: {type(exc).__name__}: {reply[:160]}"
    return [], last


# --- driver ---------------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--project", required=True)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--revision", default="18e3162")
    parser.add_argument("--gold", type=Path, default=Path("research/benchmark_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("research/results_context.json"))
    parser.add_argument("--budget", type=int, default=6000)
    parser.add_argument("--max-candidates", type=int, default=30)
    parser.add_argument("--wide-chars", type=int, default=700_000)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--model", default=None)
    parser.add_argument("--only", default="")
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to wait between calls; paces the run against subscription quota",
    )
    parser.add_argument(
        "--stop-after-errors",
        type=int,
        default=4,
        help="Give up once this many calls fail in a row; quota is gone, retry later",
    )
    args = parser.parse_args()

    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    wanted = {value.strip() for value in args.only.split(",") if value.strip()}
    if wanted:
        gold = [case for case in gold if case["id"] in wanted]

    base = args.api.rstrip("/")
    items = _request(f"{base}/api/projects/{args.project}/items")
    item_by_id = {item["id"]: item for item in items}

    wide_text, wide_stats = render_wide(corpus_files(args.repo, args.revision), args.wide_chars)
    print(
        f"wide branch: {wide_stats['files']} files, {wide_stats['rendered_chars']} chars "
        f"(~{estimate_tokens(wide_text)} est. tokens), keeping "
        f"{wide_stats['kept_fraction']:.1%} of the corpus body"
    )

    by_key: dict[tuple[str, str, int], dict] = {}
    if args.output.exists():
        for row in json.loads(args.output.read_text(encoding="utf-8")):
            by_key[(row["case_id"], row["branch"], row["repeat"])] = row
        # A row that errored is not done: quota failures must be retried, not inherited.
        done = {key for key, row in by_key.items() if not row.get("error") and row["named_paths"]}
        print(f"resuming: {len(done)} rows succeeded, {len(by_key) - len(done)} to retry")
    else:
        done = set()

    consecutive_errors = 0
    for case in gold:
        for branch in BRANCHES:
            for repeat in range(args.repeats):
                if (case["id"], branch, repeat) in done:
                    continue
                if consecutive_errors >= args.stop_after_errors:
                    print(
                        f"\nstopping: {consecutive_errors} calls failed in a row. "
                        f"Re-run the same command later to resume."
                    )
                    _write(args.output, by_key)
                    return 1
                if args.sleep:
                    time.sleep(args.sleep)
                started = time.perf_counter()
                if branch == "wide":
                    context, stats = wide_text, dict(wide_stats)
                    analysis_id = None
                else:
                    analysis = build_package(
                        base, args.project, case["change"], args.budget, args.max_candidates
                    )
                    context, stats = render_package(analysis, item_by_id)
                    analysis_id = analysis["id"]
                named, error = ask_model(context, case["change"], args.model)
                row = {
                    "case_id": case["id"],
                    "branch": branch,
                    "repeat": repeat,
                    "named_paths": named,
                    "context_chars": len(context),
                    "context_tokens_estimate": estimate_tokens(context),
                    "context_stats": stats,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    "analysis_id": analysis_id,
                    "error": error,
                    "reply_digest": hashlib.sha256(
                        json.dumps(named, sort_keys=True).encode()
                    ).hexdigest()[:16],
                }
                by_key[(case["id"], branch, repeat)] = row
                _write(args.output, by_key)
                consecutive_errors = consecutive_errors + 1 if error else 0
                flag = "!" if error else " "
                print(
                    f"{flag}{case['id']} {branch:<7} r{repeat} "
                    f"{len(named):>2} paths  {row['context_tokens_estimate']:>6} tok  "
                    f"{row['elapsed_ms'] / 1000:.1f}s {error[:60]}",
                    flush=True,
                )

    _write(args.output, by_key)
    print(f"\nWrote {len(by_key)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
