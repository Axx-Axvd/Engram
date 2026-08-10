# Retrieval results

Measured comparison of the four retrieval variants on the Engram repository. The current run uses
the **23-case** path-level gold set (`benchmark_cases.json`); the earlier ten-case run is kept below
because the expanded set **reversed its headline**.

## Setup

- **Corpus:** the Engram repository itself (dogfood), imported read-only at fixed commit
  `18e3162` through the GitHub source adapter — 423 knowledge items over 147 distinct paths,
  every one provenance-pinned. All 113 labelled gold paths exist in the corpus, so nothing in the
  gold set is unreachable by construction.
- **Typed graph:** the raw import only yields `commit -> file` provenance links, so the semantic
  graph is built deterministically from Python imports with
  [`scripts/link_python_imports.py`](../scripts/link_python_imports.py): `test -> tests -> code`
  and `code -> depends_on -> code` (194 `depends_on` + 12 `tests` links, plus the 422 imported
  `changes` links).
- **Budget:** hard 6000-token context budget, `<=30` candidates.
- **Providers:** deterministic mock LLM; real local (fastembed) embeddings.
- **Reproduce:**
  ```bash
  ENGRAM_EMBEDDING_PROVIDER=local ENGRAM_LLM_PROVIDER=mock uv run uvicorn engram.main:app
  python scripts/link_python_imports.py <project_uuid> <revision_uuid>
  python scripts/run_retrieval_experiment.py --project <project_uuid> \
      --budget 6000 --max-candidates 30 --repeats 2
  python scripts/evaluate_retrieval.py research/benchmark_cases.json research/results.json
  ```

## Current result — 23 cases, 2 repeats each (`results.json`)

| variant      | precision | recall    | F1        | false warnings | avg tokens | avg ms | non-reproducible |
|--------------|-----------|-----------|-----------|----------------|------------|--------|------------------|
| **vector**   | **0.168** | **0.381** | **0.233** | 213            | 5853       | 4949   | 0/23             |
| combined     | 0.157     | 0.283     | 0.202     | **172**        | 5998       | 9472   | 0/23             |
| graph        | 0.084     | 0.142     | 0.106     | 174            | 5998       | 10144  | 0/23             |
| full         | 0.031     | 0.106     | 0.048     | 379            | 5994       | 9426   | 0/23             |

## Reading the result

1. **The earlier "hybrid wins" claim does not survive the larger gold set.** On 23 cases plain
   vector retrieval has the best F1 (0.233) and the best recall (0.381); the hybrid is second
   (0.202). The ten-case ordering that put `combined` first is not stable, and the ten-case result
   should no longer be quoted as evidence that the typed graph improves retrieval.
2. **What the typed graph still does is suppress noise.** `combined` produces the fewest false
   warnings (172 vs 213 for `vector`) at a lower recall — it trades found paths for quieter output,
   rather than dominating on both.
3. **Graph-only retrieval is weak here, and the likely cause is structural.** The import creates one
   `changes` link from the commit item to each of the 422 files, and `changes` currently carries the
   *highest* expansion weight (0.95). One hop from any seed reaches the commit, and the second hop
   therefore reaches the whole repository at ~0.9 of the seed score — the budget fills with
   arbitrary files. This provenance star, not the semantic edges, dominates the expansion.
4. **Bounded selection still beats full context by a wide margin.** At the same 6000-token budget
   `full` remains worst (F1 0.048) with by far the most false warnings (379).
5. **Reproducibility is now actually measured.** Each case ran twice per variant: 23/23 cases
   checked, 0 non-reproducible, for all four variants. The previous "0/10 non-reproducible" was
   vacuous — a single run per case has nothing to compare against.

## Earlier ten-case runs (superseded)

Kept for the record. `results_10cases.json` (real embeddings + import graph) and
`results_baseline_mock.json` (mock embeddings, no semantic links), one run per case:

| variant  | F1 (10 cases, real emb.) | F1 (10 cases, mock emb.) |
|----------|--------------------------|--------------------------|
| combined | 0.156                    | 0.097                    |
| vector   | 0.144                    | 0.049                    |
| graph    | 0.133                    | 0.121                    |
| full     | 0.010                    | 0.020                    |

The mock-vs-real comparison still holds and is worth keeping: switching mock -> local embeddings
roughly triples the vector baseline, so the mock provider is a deterministic CI device and never a
retrieval baseline.

## Honest limitations (next steps)

- **The central hypothesis is not confirmed.** As implemented today, the typed graph does not beat
  plain semantic search on this gold set; it only reduces false warnings. Saying anything stronger
  would not be supported by these numbers.
- The `changes` provenance star is the first thing to fix: excluding provenance edges from graph
  expansion was already registered as a candidate refinement before this run, and point 3 above is
  direct evidence for it.
- The semantic graph only covers Python imports, while 13 of the 23 cases are documentation, CI or
  TypeScript changes where it has almost no useful edges.
- Absolute numbers stay low: retrieval works at file-chunk level, so a large file matches or misses
  as a whole. Sub-file chunking is the main headroom for recall.
- Single repository (dogfood). An external repository would strengthen external validity.
