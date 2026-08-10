# Engram roadmap

The authoritative direction is [`ENGRAM_TRUE_PATH_PLAN.md`](ENGRAM_TRUE_PATH_PLAN.md). Engram is a
change-impact and context-delivery layer over external sources of truth, not a documentation suite.

## Current status

The repository contains a **functional prototype of the corrected product loop**. Project
isolation, precise provenance, item-level versioning, safe review, bounded Context Packages,
read-only GitHub import, ChangeSets, CI and the interface cutover are implemented, and retrieval
has now been measured on a real imported repository against three baselines.

It is not yet a validated MVP, and the reason is now empirical rather than unmeasured: on the
23-case gold set the typed graph does **not** improve retrieval over plain semantic search — it
raises precision and cuts false warnings but loses recall. Until that changes, the core claim
stands unproven. See [`research/RESULTS.md`](research/RESULTS.md).

## Delivery sequence

### 0. Direction and baseline

**Status: implemented.**

- Keep README, roadmap and ADRs aligned with the product boundary.
- Keep pytest, Ruff, ESLint and production build green in CI.
- Freeze unrelated platform and editor work.

### 1. Project boundary and provenance

**Status: implemented and covered by isolation/migration tests.**

- Add `Project`, `Source`, `SourceRevision`, `SourceLocator` and `EvidenceRef`.
- Scope all storage and API operations by project.
- Migrate existing data into a default project without loss.

**Done when:** two projects cannot affect each other's search, links or consistency report, and
new knowledge points to an immutable source revision.

### 2. First-class items and links

**Status: implemented; legacy JSON remains a read-only compatibility representation.**

- Normalize artifact items and versions.
- Add item-level links with origin, confidence, evidence and review state.
- Preserve the document JSON only as a compatibility representation during migration.

**Done when:** one requirement, decision, component or test can be independently found, linked,
versioned and marked stale.

### 3. Safe impact analysis

**Status: implemented with atomic model-output rejection and explicit candidate review.**

- Store `ImpactAnalysis` and `ImpactCandidate` separately from source knowledge.
- Return structured, evidence-backed impact classifications.
- Require human review and remove automatic artifact rewriting.

**Done when:** running an analysis never changes active knowledge versions and every candidate is
reviewable.

### 4. Context package

**Status: implemented through API, web UI and dependency-free CLI.**

- Apply a hard token budget after typed-graph expansion and reranking.
- Persist the exact included item versions and selection explanations.
- Expose the approved package through API and CLI/MCP.

**Done when:** an external agent can reproduce and consume a bounded package without reading the
whole Engram database.

### 5. GitHub source

**Status: adapter and ChangeSet flow implemented; real-repository experiment still pending.**

- Import a fixed commit, Markdown/ADRs, issues, pull requests, changed files and tests.
- Create a new source revision on sync and mark dependent links stale.
- Connect an actual commit or pull request to an analysis through `ChangeSet`.

**Done when:** the full flow works against an existing repository and Engram never writes back to
that repository.

### 6. Research validation

**Status: measured on 23 labelled changes; the typed graph does not yet improve retrieval.**

- 23 labelled changes, 10 curated and 13 derived from real commits, each run twice.
- Full context, vector-only, graph-only and hybrid retrieval compared at an equal token budget.
- Recall, precision/F1, false warnings, context tokens, runtime and reproducibility measured; see
  [`research/RESULTS.md`](research/RESULTS.md).

**Result so far:** vector-only has the best F1 (0.233) and recall (0.381); the hybrid has the best
precision (0.185) and a third fewer false warnings, at lower recall. Bounded selection beats full
context by a wide margin. Reproducibility is exact (0/23 non-reproducible).

**Done when:** the typed graph measurably improves context selection at comparable recall — not yet
the case. Widening link extraction beyond Python imports and sub-file chunking are the open leads.

### 7. Interface cutover

**Status: implemented.**

- Center navigation on Projects, Sources, Changes, Impact analyses and Context packages.
- Present impact as an evidence table with review actions.
- Keep the editor and general graph only as diagnostic compatibility screens.

## MVP definition

Engram becomes an MVP only when a real repository can be imported at a fixed revision, a proposed
change can be analysed at item level without mutating the source of truth, a human can review every
evidence-backed candidate, an external agent can receive a bounded reproducible package, the actual
commit can be recorded as a ChangeSet, and retrieval quality has been measured against baselines.

Deferred ideas are recorded in [`FROZEN_IDEAS.md`](FROZEN_IDEAS.md), without delivery dates.
