# Retrieval results

Measured comparison of the four retrieval variants on the Engram repository, on the **23-case**
path-level gold set (`benchmark_cases.json`), every case run twice.

**Headline: at an equal token budget the hybrid now matches plain semantic retrieval on F1 while
emitting a third fewer false warnings — but it does not beat it, and the typed graph still adds no
recall.** An earlier ten-case run claimed the hybrid was ahead; that ordering did not survive the
larger set, and the current parity is a tie, not a win.

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
- **Providers:** real local (fastembed) embeddings; deterministic mock LLM. The mock proposes
  *every* retrieved element without filtering, so these numbers measure retrieval alone — and the
  filtering role a real model could play is not exercised anywhere in them.
- **Reproduce:**
  ```bash
  ENGRAM_EMBEDDING_PROVIDER=local ENGRAM_LLM_PROVIDER=mock uv run uvicorn engram.main:app
  python scripts/link_python_imports.py <project_uuid> <revision_uuid>
  python scripts/run_retrieval_experiment.py --project <project_uuid> \
      --budget 6000 --max-candidates 30 --repeats 2
  python scripts/evaluate_retrieval.py research/benchmark_cases.json research/results.json
  ```

## Current result (`results.json`)

| variant      | precision | recall    | F1        | false warnings | avg tokens | non-reproducible |
|--------------|-----------|-----------|-----------|----------------|------------|------------------|
| combined     | **0.194** | 0.292     | **0.233** | 137            | 5962       | 0/23             |
| vector       | 0.168     | **0.381** | **0.233** | 213            | 5853       | 0/23             |
| graph        | 0.143     | 0.186     | 0.162     | **126**        | 5971       | 0/23             |
| full         | 0.031     | 0.106     | 0.048     | 379            | 5994       | 0/23             |

`combined` and `vector` differ by 0.0001 in F1. That is a tie, not a ranking.

**`full` is not a baseline.** It scores every item 1.0, so its answer does not depend on the query:
all 23 cases get the same seventeen alphabetically-first files, at 5994 tokens every time. Read its
row as a sanity check on the pipeline, never as evidence about full context — see "Reading the
result", point 3.

## How the hybrid got here

Two structural defects were found by measurement and fixed. Neither is weight tuning: both change
what the graph is allowed to mean.

1. **The provenance star.** A GitHub import creates one `changes` link from the commit item to
   every file it touched (422 of them), and `changes` carried the highest expansion weight. One hop
   from any seed reached the commit and the second reached the whole repository at ~0.9 of the seed
   score. Expansion now skips `changes` links whose source is a commit or pull request — those
   record what a revision touched. `changes` from a change request is kept: that one is intent.
2. **Expansion ran against the direction of impact.** Typed links point from the dependent element
   to the one it relies on (`test -> tests -> code`, `code -> depends_on -> code`,
   `task -> implements -> requirement`), but traversal was undirected. Half of every expansion
   therefore walked into what an element *uses* — the shared models, enums and error helpers that
   almost nothing changes — instead of what depends on it. Expansion now follows the reverse
   direction for dependency-shaped links, and each origin's contribution is damped by its fan-out
   (`1 / (1 + log(1 + n - 1))`), because an element reaching twenty neighbours says less about each
   one. Both the fan-out and the damping factor are recorded in `selection_reason`.

| `combined`             | precision | recall | F1    | false warnings |
|------------------------|-----------|--------|-------|----------------|
| with provenance star   | 0.157     | 0.283  | 0.202 | 172            |
| star excluded          | 0.185     | 0.283  | 0.224 | 141            |
| + directed and damped  | 0.194     | 0.292  | 0.233 | 137            |

`graph` alone improved along the same path: F1 0.106 -> 0.140 -> 0.162. `vector` and `full` do not
expand and their outputs are byte-identical across all three runs — a control confirming each
change touched only what it was meant to touch. Raw runs: `results_before_graph_fix.json`,
`results_undirected_graph.json`, `results.json`.

**Runtime is not measured reliably here and no speed claim is made.** The unchanged `vector`
variant averaged 4949 ms, 1295 ms and 3263 ms across the three runs while producing identical
output, so per-analysis timings are dominated by machine load, not by these changes.

## Where the graph helps and where it hurts

Splitting the gold set by whether the Python import graph has any edges in that region:

| subset                                | best F1                  | runner-up        |
|---------------------------------------|--------------------------|------------------|
| 15 cases touching the Python backend  | vector **0.220**         | combined 0.185   |
| 8 documentation / CI / web cases      | combined **0.359**       | vector 0.261     |

This is the opposite of the intuitive story, and it is the most useful thing the expanded set
revealed. The hybrid wins where the typed graph is *absent* — on documentation and CI changes its
advantage comes from lexical matching, since those change requests share literal terms with their
targets. Where the graph is *active*, plain vector retrieval is still better: expansion continues
to spend budget on neighbours that are not in the gold set, and recall drops from 0.311 to 0.211.

An import edge is evidently a weak predictor of "will need editing together". That is a finding
about the edge type, not proof that typed graphs cannot work.

## Does a different edge type help? (co-change probe)

The diagnosis above says an import edge is a weak predictor of "changes together", so the obvious
test is to build the graph from exactly that relation: files that appeared in the same commit.
[`scripts/link_cochange.py`](../scripts/link_cochange.py) mines those edges, and the probe replaced
the import graph with them rather than adding to it, so the two edge types are compared alone.

Guards, because the gold set is itself commit-derived:

- **Leave-one-out.** A case derived from commit `C` is evaluated on a graph mined without `C`.
  14 folds, edge set rebuilt per fold.
- **No looking ahead.** Only history reachable from the pinned revision `18e3162` is mined; commits
  made after the analysed snapshot are knowledge the analysis could not have had.
- Same `<=15 importable files` rule as the gold set, so milestone commits cannot form huge cliques.

| variant (co-change) | precision | recall | F1        | false warnings |
|---------------------|-----------|--------|-----------|----------------|
| combined            | 0.169     | 0.283  | 0.212     | 157            |
| graph               | 0.114     | 0.168  | 0.136     | 148            |

**Co-change edges did worse than import edges** (combined 0.212 vs 0.233, graph 0.136 vs 0.162).
Co-change links are `related_to` and expand at weight 0.55 against 0.8/0.88 for import links, so a
control run repeated the probe with the weight matched at 0.8: combined 0.213, graph 0.135 — the
weight explains nothing (`results_cochange.json`, `results_cochange_weight_matched.json`).

The probe was **biased in co-change's favour and still lost**. This repository has only 15 commits
that qualify, and neighbouring commits touch overlapping files, so even after leave-one-out a case
keeps edges directly between its own gold paths — 47 of them for ENG-023, 10 for ENG-014. On a
history this short, "changed together before" and "is the answer" nearly coincide; a positive result
would have been memorisation. A negative one under that bias is informative.

## The recall ceiling is the real finding

Across five graph configurations, `combined` recall barely moves, while vector-only retrieval sits
far above all of them:

| graph configuration                 | recall | F1    |
|-------------------------------------|--------|-------|
| commit provenance star              | 0.283  | 0.202 |
| star excluded                       | 0.283  | 0.224 |
| directed + fan-out damped (imports) | 0.292  | 0.233 |
| co-change, leave-one-out            | 0.283  | 0.212 |
| co-change, weight matched           | 0.283  | 0.213 |
| **no graph at all (vector)**        | **0.381** | 0.233 |

Changing the edge type, the direction, the weights and the hub handling changed *which wrong items
entered the budget*, not *how many right ones were found*. That points away from edge quality and
at the mechanism: under a fixed budget, expansion competes with retrieval for the same ~30 slots,
and a neighbour that displaces a correct semantic hit has to be correct itself to break even —
which, in this corpus, it rarely is.

Two honest readings follow, and they suggest different work. Either expansion must stop competing
(a reserved quota, or admitting a neighbour only when it also has semantic support), or the typed
graph's value is not in *selecting* context at all but in explaining and dating it — in which case
that is what should be measured.

## Reading the result

1. **The hypothesis is still not confirmed.** The hybrid matches semantic search; it does not beat
   it. Recall is strictly worse (0.292 vs 0.381) — under a fixed budget the graph's neighbours
   displace correct vector hits, and no edge type tried so far changes that.
2. **What the graph reliably buys is quiet, precise output.** Best precision (0.194) and 36% fewer
   false warnings (137 vs 213) at equal budget. For a reviewer reading candidates by hand, that is
   worth something; it is not the same claim as better retrieval.
3. **The `full` baseline is degenerate and its 0.048 proves nothing. Retracted, 2026-08-12.** This
   line previously read "bounded selection still beats full context by a wide margin" and was
   published as the one firmly established positive. It is not. In `full` mode every item is scored
   `1.0` ([`context_service.py:239-240`](../apps/api/src/engram/services/context_service.py#L239-L240))
   and every item seeds the selection, after which the same 6000-token budget truncates. The result
   is **query-independent**: across 23 cases and both repeats the variant returns *one identical set
   of 17 paths* — the alphabetically first files in the repository, starting at
   `.claude/agents/frontend-architect.md`, `Claude.md`, `DESIGN.md`. Average tokens is 5994 in every
   single row.

   So 0.233 against 0.048 says only that ranked retrieval beats answering every question with the
   same seventeen files. It is a sanity check on the code, not evidence that bounded selection is
   valuable, and the founding premise — §2.2.1 of the specification, "even a large context window is
   not enough as the only project memory" — has never been tested, because the baseline it names was
   never run. The corpus is roughly 205k tokens; a long-context model reading all of it was never a
   variant.
4. **Reproducibility is measured, not assumed.** Every case ran twice per variant: 23/23 checked,
   0 non-reproducible, all four variants.

## Earlier ten-case runs (superseded)

`results_10cases.json` (real embeddings + import graph) and `results_baseline_mock.json` (mock
embeddings, no semantic links), one run per case:

| variant  | F1 (10 cases, real emb.) | F1 (10 cases, mock emb.) |
|----------|--------------------------|--------------------------|
| combined | 0.156                    | 0.097                    |
| vector   | 0.144                    | 0.049                    |
| graph    | 0.133                    | 0.121                    |
| full     | 0.010                    | 0.020                    |

The ten-case ordering put `combined` first on a 0.012 gap and should not be quoted: it did not hold
at 23 cases. The mock-vs-real comparison does still hold — switching mock -> local embeddings
roughly triples the vector baseline, so the mock provider is a deterministic CI device and never a
retrieval baseline.

## Honest limitations (next steps)

- **The LLM's filtering role is untested.** The mock passes every retrieved element through, so
  pipeline precision equals retrieval precision. A real model asked to drop irrelevant candidates
  attacks exactly the metric the hybrid is meant to win, and has never been measured.
- Retrieval works at file-chunk level, so a large file matches or misses as a whole. Sub-file
  chunking is the main headroom for the low absolute recall.
- Co-change edges have now been tried and did worse than import edges, under a bias that favoured
  them. Mining them on a repository with real history (thousands of commits) is the only way to
  give that idea a fair test — 15 qualifying commits cannot support it.
- 23 cases is small: a 0.0001 F1 gap is noise, and even the subset splits (15 and 8 cases) are
  indicative rather than conclusive.
- The gold-set file itself lives in the imported corpus and competes for budget (858 tokens in one
  observed package). It cannot inflate recall, since it is never a gold path, but excluding
  `research/` from the corpus would make the setup cleaner.
- Single repository (dogfood). An external repository would strengthen external validity.

## The project's second measured negative

The direction this result opened — capturing rationale from agent sessions, since retrieval turned
out not to be the bottleneck — was itself gated on a premise check and did not pass it. Of 29
decisions of this project, one has its rationale recorded only in a session transcript: 3.4% against
a 30% threshold registered before the labelling started. Method, numbers and citations:
[`DECISION_PROVENANCE.md`](DECISION_PROVENANCE.md).
