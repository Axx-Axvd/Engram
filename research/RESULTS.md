# Retrieval results

Measured comparison of the four retrieval variants on the Engram repository, on the **23-case**
path-level gold set (`benchmark_cases.json`), every case run twice.

**Headline: the central hypothesis is not confirmed.** At an equal token budget the typed graph does
not beat plain semantic retrieval on F1. It buys precision and quiet output at the cost of recall.
An earlier ten-case run suggested the opposite; that ordering did not survive the larger set.

## Setup

- **Corpus:** the Engram repository itself (dogfood), imported read-only at fixed commit
  `18e3162` through the GitHub source adapter — 423 knowledge items over 147 distinct paths,
  every one provenance-pinned. All 113 labelled gold paths exist in the corpus, so nothing in the
  gold set is unreachable by construction.
- **Typed graph:** the raw import only yields `commit -> file` provenance links, so the semantic
  graph is built deterministically from Python imports with
  [`scripts/link_python_imports.py`](../scripts/link_python_imports.py): `test -> tests -> code`
  and `code -> depends_on -> code` (194 `depends_on` + 12 `tests` links).
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

## Current result (`results.json`)

| variant      | precision | recall    | F1        | false warnings | avg tokens | avg ms | non-reproducible |
|--------------|-----------|-----------|-----------|----------------|------------|--------|------------------|
| **vector**   | 0.168     | **0.381** | **0.233** | 213            | 5853       | 1295   | 0/23             |
| combined     | **0.185** | 0.283     | 0.224     | 141            | 5982       | 1825   | 0/23             |
| graph        | 0.120     | 0.168     | 0.140     | **139**        | 5977       | 1802   | 0/23             |
| full         | 0.031     | 0.106     | 0.048     | 379            | 5994       | 4095   | 0/23             |

## Reading the result

1. **Vector-only wins on F1 and recall; the hybrid wins on precision and noise.** `combined` finds
   correct paths at the highest rate per returned path (0.185) and emits a third fewer false
   warnings (141 vs 213), but it recovers noticeably fewer of the truly affected paths (0.283 vs
   0.381). Under a fixed budget, graph-expanded neighbours displace good vector hits. Net F1 lands
   just below vector-only.
2. **The typed graph is not currently earning its place in retrieval.** What it demonstrably
   provides is noise suppression, not better coverage. Any stronger claim would not be supported by
   these numbers. This is a measured negative result for the hypothesis as implemented — not a
   reason to remove the graph, which also carries the explanation and provenance the product needs,
   but a reason not to advertise it as a retrieval improvement yet.
3. **Bounded selection still beats full context by a wide margin.** At the same budget `full` is
   worst on every metric (F1 0.048, 379 false warnings). Explaining and bounding the selection is
   the part that clearly pays off.
4. **Reproducibility is measured, not assumed.** Each case ran twice per variant: 23/23 cases
   checked, 0 non-reproducible, all four variants. A fixed revision plus deterministic providers
   yields identical selection snapshots.

## The provenance-star fix

The first 23-case run exposed a structural defect rather than a tuning problem. A GitHub import
creates one `changes` link from the commit item to **every** file it touched (422 of them), and
`changes` carried the highest expansion weight (0.95). One hop from any seed reached the commit and
the second hop reached the entire repository at ~0.9 of the seed score, so the budget filled with
arbitrary files.

Excluding provenance edges from expansion had been registered as a candidate refinement *before*
these numbers existed. `changes` links from a commit or pull request are now skipped during
expansion (they record what a revision touched); `changes` from a change request is kept, because
that one is intent rather than provenance.

Effect, same gold set and budget (`results_before_graph_fix.json` -> `results.json`):

| variant  | F1            | precision     | false warnings | avg ms          |
|----------|---------------|---------------|----------------|-----------------|
| combined | 0.202 → 0.224 | 0.157 → 0.185 | 172 → 141      | 9472 → 1825     |
| graph    | 0.106 → 0.140 | 0.084 → 0.120 | 174 → 139      | 10144 → 1802    |
| vector   | 0.233 (same)  | 0.168 (same)  | 213 (same)     | 4949 → 1295     |
| full     | 0.048 (same)  | 0.031 (same)  | 379 (same)     | 9426 → 4095     |

`vector` and `full` do not use graph expansion and their scores are byte-identical before and
after — a control confirming the change touched only what it was meant to touch. Recall of
`combined` is also unchanged (0.283): removing the star deleted noise, but the typed graph still
contributed no additional correct path.

## Earlier ten-case runs (superseded)

`results_10cases.json` (real embeddings + import graph) and `results_baseline_mock.json` (mock
embeddings, no semantic links), one run per case:

| variant  | F1 (10 cases, real emb.) | F1 (10 cases, mock emb.) |
|----------|--------------------------|--------------------------|
| combined | 0.156                    | 0.097                    |
| vector   | 0.144                    | 0.049                    |
| graph    | 0.133                    | 0.121                    |
| full     | 0.010                    | 0.020                    |

The ten-case ordering put `combined` first and should no longer be quoted: it did not hold at 23
cases. The mock-vs-real comparison does still hold — switching mock -> local embeddings roughly
triples the vector baseline, so the mock provider is a deterministic CI device and never a
retrieval baseline.

## Honest limitations (next steps)

- The semantic graph only covers Python imports, while 13 of the 23 cases are documentation, CI or
  TypeScript changes where it has almost no useful edges. Widening link extraction is the most
  direct way to give the graph a fair chance.
- Retrieval works at file-chunk level, so a large file matches or misses as a whole. Sub-file
  chunking is the main headroom for the low absolute recall.
- Under a fixed budget the hybrid trades recall for precision. Whether that trade is right depends
  on what the agent needs, which argues for measuring downstream task success, not only retrieval
  metrics.
- Single repository (dogfood). An external repository would strengthen external validity.
