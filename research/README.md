# Retrieval experiment

`benchmark_cases.json` is the first ten-change, path-level gold set for the Engram repository. It
is deliberately small: it exists to validate the experiment pipeline before annotation expands to
20–30 changes and before the corrected MVP can be claimed.

Import the repository into one Engram project, keep the deterministic mock provider for baseline
runs, and export all four variants:

```bash
python scripts/run_retrieval_experiment.py --project <uuid> --output research/results.json
```

The runner creates non-mutating impact analyses and exports one JSON array containing rows like:

```json
{
  "case_id": "ENG-001",
  "variant": "combined",
  "retrieved_paths": ["apps/api/src/engram/models/project.py"],
  "token_estimate": 500,
  "elapsed_ms": 42,
  "snapshot_digest": "stable-digest"
}
```

Use the variant names `full`, `vector`, `graph`, and `combined`, then run:

```bash
python scripts/evaluate_retrieval.py research/benchmark_cases.json results.json
```

The report contains micro precision/recall/F1, false warnings, average tokens and time, plus the
number of cases whose repeated snapshots were not reproducible.

A raw GitHub import only produces `commit -> file` provenance links, so the semantic typed graph is
built deterministically from Python imports with `scripts/link_python_imports.py` before the graph
and combined variants are meaningful. The first measured comparison (mock baseline vs. real
embeddings plus the import graph) and how to reproduce it are written up in
[`RESULTS.md`](RESULTS.md), with the raw runs in `results.json` and `results_baseline_mock.json`.
