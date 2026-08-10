# Retrieval experiment

`benchmark_cases.json` is the path-level gold set for the Engram repository: **23 labelled
changes**, each one a change request plus the set of repository paths a correct impact analysis
should surface.

## How cases are labelled

Every case carries an `origin` field so the label can be audited:

- **`curated` (10 cases, `ENG-001`…`ENG-010`).** Hand-written from the corrected product model:
  one change request per core capability (project boundary, provenance, item versioning, safe
  review, budget, GitHub import, CI, interface). Ground truth is the set of files a maintainer
  would have to open.
- **`commit <sha>` (13 cases, `ENG-011`…`ENG-023`).** Derived from real non-merge commits of this
  repository, which makes the label objective rather than a matter of opinion. The protocol:
  1. Take the commit's changed files.
  2. Keep only paths that **exist in the analysed revision** and whose suffix the GitHub adapter
     actually imports (`.md`, `.py`, `.ts`, `.tsx`, `.json`, `.yml`, `.toml`, …) — a path that was
     never ingested cannot be retrieved, and scoring it would only add constant noise.
  3. Use the commit only if it touches **≤ 15 importable files**, so a case describes one change
     rather than a milestone. This rule is applied before any measurement, never to shape a result.
  4. Write the change text from the commit's **intent**, without naming files, directories or
     symbols, so no variant can win by copying the query.

Cases whose entire footprint was later deleted or renamed away are not usable at a fixed revision
and were dropped; near-duplicate labels (several documentation-only commits touching the same
single file) were dropped as well.

## Running it

Import the repository into one Engram project, then export all four variants:

```bash
python scripts/run_retrieval_experiment.py --project <uuid> --output research/results.json
```

The runner creates non-mutating impact analyses and writes one JSON array of rows:

```json
{
  "case_id": "ENG-001",
  "variant": "combined",
  "repeat": 0,
  "retrieved_paths": ["apps/api/src/engram/models/project.py"],
  "token_estimate": 500,
  "elapsed_ms": 42,
  "snapshot_digest": "stable-digest"
}
```

Variant names are `full`, `vector`, `graph` and `combined`. Score them with:

```bash
python scripts/evaluate_retrieval.py research/benchmark_cases.json research/results.json
```

The report contains micro precision/recall/F1, false warnings, average tokens and time, and the
reproducibility check.

## Reproducibility is only measured with repeats

`--repeats N` runs every case and variant `N` times. **A single run per case cannot detect
non-reproducibility** — there is nothing to compare its selection snapshot against, so the check
reports a vacuous zero. With `N > 1` the evaluator compares the snapshot digests of the repeated
runs and reports `repeated_cases` (how many cases were actually checked) next to
`non_reproducible_cases`. Quality metrics are scored from the first run of each case, so adding
repeats tests stability without inflating the absolute counts.

A raw GitHub import only produces `commit -> file` provenance links, so the semantic typed graph is
built deterministically from Python imports with `scripts/link_python_imports.py` before the graph
and combined variants are meaningful. Measured comparisons and how to reproduce them are written up
in [`RESULTS.md`](RESULTS.md), with the raw runs in `results.json` (current, 23 cases),
`results_10cases.json` and `results_baseline_mock.json` (earlier ten-case runs).
