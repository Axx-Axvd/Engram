# Engram roadmap

The authoritative direction is [`ENGRAM_TRUE_PATH_PLAN.md`](ENGRAM_TRUE_PATH_PLAN.md) together with
[`ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md`](ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md), which records what the
comparative measurement disproved and where the effort moves next. Engram indexes external sources of
truth and delivers bounded, evidence-backed context; it is not a documentation suite.

## Current status

The repository contains a **functional prototype of the corrected product loop**. Project
isolation, precise provenance, item-level versioning, safe review, bounded Context Packages,
read-only GitHub import, ChangeSets, an MCP channel, CI and the interface cutover are implemented,
and retrieval has been measured on a real imported repository against three baselines.

**The central retrieval hypothesis is disproved.** On the 23-case gold set the typed graph does not
improve context selection: the hybrid ties plain semantic search on F1 (0.2332 vs 0.2331) and loses
recall (0.292 vs 0.381), winning only precision and false-warning count. Five graph configurations —
including co-change edges mined from git history — leave recall at 0.283–0.292 against 0.381 without
any graph. The bottleneck is the fixed budget, not the edge type. See
[`research/RESULTS.md`](research/RESULTS.md) and [`docs/adr/ADR-002`](docs/adr/ADR-002-project-memory-from-agent-sessions.md).

Effort therefore moves to the part of the original value list that was never measured: preserving
rationale between sessions, and context cost. Stages 8–10 below are gated on a cheap premise check
whose kill criterion is registered in advance.

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

**Status: implemented through API, web UI, dependency-free CLI and an MCP stdio channel.**

- Apply a hard token budget after typed-graph expansion and reranking.
- Persist the exact included item versions and selection explanations.
- Expose the approved package through API, CLI and MCP (`engram.mcp.server`: `list_projects`,
  `analyze_change`, `get_context`, `list_context_packages`; candidate review stays human-only).

**Done when:** an external agent can reproduce and consume a bounded package without reading the
whole Engram database. Verified over the real protocol: analyse → blocked while review is pending →
bounded package with sources and reasons after approval.

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

**Result: the hypothesis is disproved.** The hybrid and vector-only tie on F1 (0.233 both); the hybrid
has the best precision (0.194) and 36% fewer false warnings, vector-only the best recall (0.381 vs
0.292). Two structural defects were found and fixed by measurement — the commit provenance star and
undirected expansion — lifting the hybrid from F1 0.202 to 0.233 without moving the recall ceiling.
Co-change edges mined from git history, the most direct test of "the edge type is wrong", did worse
(0.212) under a setup biased in their favour. Bounded selection still beats full context by a wide
margin (0.233 vs 0.048), and reproducibility is exact (0/23).

**Conclusion:** across five graph configurations recall stays at 0.283–0.292 against 0.381 with no
graph at all. The limit is the fixed budget, where expansion competes with retrieval, not the quality
of the edges. Further weight and edge-type tuning for retrieval metrics is frozen; see
[`docs/adr/ADR-002`](docs/adr/ADR-002-project-memory-from-agent-sessions.md).

### 7. Interface cutover

**Status: implemented.**

- Center navigation on Projects, Sources, Changes, Impact analyses and Context packages.
- Present impact as an evidence table with review actions.
- Keep the editor and general graph only as diagnostic compatibility screens.

### 8. Premise check for project memory (gate)

**Status: next. No product code is written at this stage.**

- Label ~20 real decisions of this project on three independent axes: where the conclusion is
  recorded, where the rationale is, where the rejected alternatives are — one of code, ADR, doc,
  commit, transcript, nowhere.
- Report the share whose rationale or alternatives exist **only** in a session transcript.

**Kill criterion, registered before measuring:** below 30%, the niche is already covered by commits
and documentation. The direction is closed, the result is recorded in `research/RESULTS.md` as a
second measured negative, and only stage 10b remains.

### 9. Agent sessions as a source

**Status: blocked on stage 8.**

- Ingest a session as `SourceKind.agent_session`: revision is the session id, a locator is a range of
  messages, an extracted decision is a versioned `decision` item.
- Segment a session before extracting, and degrade a wide-fan-out segment to `proposed` links — an
  unsegmented session would recreate the provenance star stage 6 exposed.
- Link `code_component --implements--> decision` for files edited in the same segment.
- Never persist raw messages: only extracted decision text plus the locator that lets a human verify
  it. No schema migration is required for any of this.
- Serve rationale by direct link lookup, and expose it as a `why` tool on the MCP channel.

**Done when:** an external agent asks which decisions govern a set of files and receives them with
their session and message range, not "similar files".

### 10. Measuring the new claim

**Status: blocked on stage 9.**

- **a. Decision adherence (the thesis claim).** ~15 tasks built from real decisions whose violation is
  detectable *mechanically*, with no model acting as judge. Each task is solved twice — with the
  agent's own search and with rationale available — and the violation rate is compared.
- **b. Context cost (an engineering property, not a research claim).** Tokens and steps to the same
  outcome, with and without a prepared package, over the existing 23 cases.

**Done when:** 10a gives an unambiguous answer, and no statement in `README.md`, `ROADMAP.md` or
`research/RESULTS.md` is stronger than the numbers support.

## MVP definition

Every mechanical condition is met: a real repository imports at a fixed revision, a change is analysed
at item level without mutating the source of truth, a human reviews every evidence-backed candidate,
an external agent receives a bounded reproducible package over CLI or MCP, the actual commit is
recorded as a ChangeSet, and retrieval quality has been measured against baselines.

What is missing is not a mechanism but a demonstrated advantage. The measurement came back at parity,
so Engram is a working system without a proven reason to exist yet. It becomes an MVP when one claim
is measured and holds — currently stage 10a, decision adherence — and not before.

Deferred ideas are recorded in [`FROZEN_IDEAS.md`](FROZEN_IDEAS.md), without delivery dates.
