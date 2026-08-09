# First retrieval results

First measured comparison of the four retrieval variants on the ten-change, path-level gold set
(`benchmark_cases.json`). These are early numbers on a deliberately small set; the contribution is
the **relative ordering** of the methods, not the absolute scores.

## Setup

- **Corpus:** the Engram repository itself (dogfood), imported read-only at fixed commit
  `18e3162` through the GitHub source adapter (423 knowledge items, provenance-pinned).
- **Typed graph:** the raw import only yields `commit -> file` provenance links, so the semantic
  graph is built deterministically from Python imports with
  [`scripts/link_python_imports.py`](../scripts/link_python_imports.py): `test -> tests -> code`
  and `code -> depends_on -> code`, resolved to file level via a module **and** symbol map
  (194 `depends_on` + 12 `tests` links).
- **Budget:** hard 6000-token context budget (a realistic single-package slice), `<=30` candidates.
- **Providers:** deterministic mock LLM for reproducibility; embeddings compared below.
- **Reproduce:**
  ```bash
  # server with real embeddings; mock LLM; read-only GitHub token in-process only
  ENGRAM_EMBEDDING_PROVIDER=local ENGRAM_LLM_PROVIDER=mock uv run uvicorn engram.main:app
  python scripts/link_python_imports.py <project_uuid> <revision_uuid>
  python scripts/run_retrieval_experiment.py --project <project_uuid> --budget 6000 --max-candidates 30
  python scripts/evaluate_retrieval.py research/benchmark_cases.json research/results.json
  ```

## Baseline — mock embeddings, no semantic links (`results_baseline_mock.json`)

| variant  | precision | recall | F1    | false warnings | avg tokens | non-reproducible |
|----------|-----------|--------|-------|----------------|------------|------------------|
| graph    | 0.087     | 0.200  | 0.121 | 84             | 5999       | 0/10             |
| combined | 0.067     | 0.175  | 0.097 | 97             | 5998       | 0/10             |
| vector   | 0.033     | 0.100  | 0.049 | 118            | 5895       | 0/10             |
| full     | 0.013     | 0.050  | 0.020 | 158            | 5999       | 0/10             |

## Fair test — real embeddings + import graph (`results.json`)

| variant      | precision | recall | F1        | false warnings | avg tokens | non-reproducible |
|--------------|-----------|--------|-----------|----------------|------------|------------------|
| **combined** | **0.114** | 0.250  | **0.156** | 78             | 5998       | 0/10             |
| vector       | 0.097     | 0.275  | 0.144     | 102            | 5932       | 0/10             |
| graph        | 0.100     | 0.200  | 0.133     | 72             | 5998       | 0/10             |
| full         | 0.006     | 0.025  | 0.010     | 169            | 5994       | 0/10             |

## Reading the result

1. **The hybrid wins.** `combined` (vector + typed graph + reranking under budget) has the best F1,
   ahead of vector-only, graph-only and full context. The typed graph adds precision: `combined`
   raises precision over `vector` (0.114 vs 0.097) and cuts false warnings (78 vs 102) while keeping
   comparable recall; `graph` has the fewest false warnings of all (72).
2. **Real embeddings are essential.** Switching mock -> local (fastembed) roughly triples the vector
   baseline (F1 0.049 -> 0.144). The mock provider is only a deterministic CI/test device, never a
   retrieval baseline.
3. **Bounded selection beats full context.** At the same 6000-token budget, `full` is far worst
   (F1 0.010): dumping arbitrary items wastes the budget. Explaining and bounding the selection is
   the point.
4. **Reproducible.** Every variant is 0/10 non-reproducible — a fixed revision plus deterministic
   providers yields identical selection snapshots.

## Honest limitations (next steps)

- Only 10 gold cases; expand to 20–30 for statistical weight.
- Absolute recall is modest (~0.25). Headroom: code chunking below file level, better change-query
  phrasing, wider link coverage (imports miss dynamic/string references), and weight tuning.
- The `commit -> file` provenance star is still present; excluding `changes` links from graph
  expansion (they are provenance, not forward dependencies) is a candidate algorithm refinement.
- Single repository (dogfood). An external repository would strengthen external validity.
