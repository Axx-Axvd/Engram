# Engram

English | [Русский](README.ru.md)

**The short version, if you're in a hurry.** Engram is a working system that indexes a project's
source files, keeps an exact reference to the original source for every piece of knowledge, and
assembles a small context package for an AI agent instead of dumping the entire repository on it.
The system is built, tested, and operational. But it rested on three assumptions about **why** it
was needed. All three were tested through measurement — and none was confirmed. This file gives
an honest account of how that happened and what follows from it.

If programming isn't your field, that's fine — everything below is explained in plain language.

---

## Contents

1. [How it started: the problem](#1-how-it-started-the-problem)
2. [The proposed solution](#2-the-proposed-solution)
3. [What was actually built](#3-what-was-actually-built)
4. [How you test something like this](#4-how-you-test-something-like-this)
5. [First test: does the relationship map help?](#5-first-test-does-the-relationship-map-help)
6. [Second test: does project intent exist only in AI conversations?](#6-second-test-does-project-intent-exist-only-in-ai-conversations)
7. [Third test: uncovering our own self-deception](#7-third-test-uncovering-our-own-self-deception)
8. [Fourth test: halted](#8-fourth-test-halted)
9. [Conclusions](#9-conclusions)
10. [What the process itself taught us](#10-what-the-process-itself-taught-us)
11. [Technical details](#11-technical-details)

---

## 1. How it started: the problem

The project began on May 26, 2026. Its working title was **"a project memory layer for long-running
AI projects."**

The idea behind it was simple and, at first glance, hard to dispute. Imagine a software project
that runs for a year or two. Over that time, it accumulates:

- the original description of what you wanted to build;
- requirements and their endless refinements;
- architectural decisions ("we'll use this database, not that one — and here's why");
- tasks, tests, and fixes;
- the code itself, which keeps changing throughout.

When a human ran the project, all of this somehow lived in their head and in conversations. But now
an AI agent does a substantial share of the work. That exposes five problems, listed in the
project's original specification:

| No. | Subproblem | In plain language |
|---|---|---|
| 1 | Context limits | A model can receive only a limited amount of text at once. The whole project won't fit |
| 2 | Noise and forgetting | The longer the history, the harder it is for the model to rely on what matters. **Earlier agreements get lost** |
| 3 | Artifact drift | A requirement changes, but the corresponding tasks and tests aren't updated — and nobody notices |
| 4 | Poor change-impact analysis | A change request arrives, but it's unclear what exactly it will affect |
| 5 | Token costs | Giving every agent half the project at every step is expensive and slow |

Of these five, problem No. 2 feels most acute when working with AI. You spend an hour discussing
with a model why something must not be done a certain way, reach a decision — then start a new
session the next day, and all of it is gone. The model remembers neither the decision nor which
alternatives you rejected and why.

The original specification's conclusion was that we need a system that doesn't just call models,
but **manages project memory** — storing knowledge persistently and selecting the **minimum
necessary context** for a specific task.

---

## 2. The proposed solution

The project's main bet was expressed as follows:

> If we break project knowledge into **small, separate items**, connect them with **typed
> relationships** (here is a requirement, here is the code that implements it, here is the test
> that checks it), and retrieve context not just **by meaning**, but also **through those
> relationships**, we should be able to select context more accurately than ordinary search.

The key concept is the **relationship graph**. Ordinary search ("find text fragments similar to my
query") doesn't know about these relationships. It finds a file containing similar words. A
relationship graph knows that if this requirement changes, you also need to look at the test that
checks it — even if the test has no words in common with the query.

Here is how it works:

```text
   a pinned source revision (a specific GitHub commit)
                    │
                    ▼
   small knowledge items + typed relationships between them
   (requirement, decision, code, test — with "implements", "tests", "depends on" edges)
                    │
                    ▼
   change request → impact analysis → human review
                    │
                    ▼
   a bounded context package for an AI agent
                    │
                    ▼
   actual commit → record "request → what changed" → consistency check
```

Three principles have been built into the design from the start:

- **Provenance.** Every piece of knowledge records where it came from: which source, which pinned
  revision, and exactly which lines. Not "the model said so," but "here is the file, here is the
  commit, here are lines 40–58."
- **No automatic changes.** Analysis only makes suggestions. Not a single line changes without
  explicit human confirmation. External systems — GitHub and issue trackers — remain the source
  of truth.
- **A hard budget.** A context package cannot exceed its specified size. The limit is applied
  **after** the system traverses the relationships, not before.

---

## 3. What was actually built

Everything listed here is working, tested code — not a plan.

| Component or capability | Status |
|---|---|
| FastAPI + PostgreSQL + pgvector backend | working |
| Strict project isolation (data from different projects never overlaps anywhere) | working |
| Immutable provenance: source → revision → exact location | working |
| Item-level versioning: editing one item leaves its neighbors untouched | working |
| Typed relationships with evidence and human confirmation | working |
| Impact analysis that changes nothing | working |
| Atomic validation of model responses: an invalid response is rejected in full | working |
| Reproducible context packages with a hard budget | working |
| Read-only GitHub import at a fixed commit | working |
| MCP channel: an external AI agent can request analysis and retrieve a package itself | working |
| Next.js web interface | working |
| 58 tests against a real database, linters, and GitHub Actions CI | passing |

The project consists of 31 commits written over 7 active days of work.

---

## 4. How you test something like this

Before looking at the results, we need to explain how to measure whether a system selects context
well or poorly. This takes two minutes, and the rest will then make sense.

### The reference dataset

Take 23 actual changes to the project. For each one, record **manually and in advance** which files
actually had to be touched. This is the reference, or "gold" dataset. Ten changes were constructed
manually around the product's key capabilities; thirteen were derived from actual commits
(take a commit, look at the files it changed — that is the correct answer).

Then give the system the change description and see which files it names.

### Three numbers

Suppose a change actually affects **5 files**. The system names **8 files**, of which **4** are
correct.

**Precision** is the proportion of the system's selections that turned out to be correct:

```
precision = correctly selected / total selected = 4 / 8 = 0.50
```

In other words, half the answer is noise that a human will have to filter out manually.

**Recall** is the proportion of the required files that the system found:

```
recall = correctly selected / total required = 4 / 5 = 0.80
```

In other words, the system missed one necessary file.

These two numbers pull in different directions. You could name every file in the project — recall
would be 100%, but precision would be close to zero, and the answer would be useless. You could name
one file you're certain about — precision would be 100%, but recall would be tiny.

**F1** combines them into one number so that you can't succeed at one by sacrificing the other:

```
F1 = 2 × precision × recall / (precision + recall) = 2 × 0.5 × 0.8 / 1.3 ≈ 0.62
```

This is the harmonic mean. Its defining property: if either number is close to zero, F1 collapses
too, however good the other number is. That is why it serves as the primary metric.

### Experimental conditions

- Corpus: the Engram repository itself, imported at the pinned commit `18e3162` — 423 knowledge
  items across 147 files, each with recorded provenance.
- Budget: 6000 tokens. A token is roughly 4 characters, so this is about 24,000 characters, or
  twelve pages of ordinary text.
- Each case is run twice to check reproducibility.
- Four context-selection methods are compared.

---

## 5. First test: does the relationship map help?

This was the project's central hypothesis. We compared four ways of assembling context under the
same budget:

- **vector** — ordinary semantic search, with no graph;
- **graph** — relationships only;
- **combined** — a hybrid: search plus relationship expansion (the "Engram approach");
- **full** — "give me more of everything," the control.

### Results

| method | precision | recall | F1 | false positives |
|---|---|---|---|---|
| **combined** (Engram) | **0.194** | 0.292 | **0.233** | 137 |
| **vector** (ordinary search) | 0.168 | **0.381** | **0.233** | 213 |
| graph (relationships only) | 0.143 | 0.186 | 0.162 | **126** |
| full (control) | 0.031 | 0.106 | 0.048 | 379 |

**The hypothesis was not confirmed.** The F1 gap between the hybrid and ordinary search was 0.0001.
That is not a win; it is a tie — with a sample this size, such a difference means nothing at all.

The hybrid has better precision and a third fewer false positives — a welcome improvement for
someone who has to inspect the candidate list manually. But it loses substantially on recall:
0.292 versus 0.381. In other words, it finds **less** of what is needed.

### Attempts to rescue the hypothesis

Before accepting defeat, we found and fixed two genuine defects.

**First defect: the "provenance star."** During import, the system created a "this commit changed
this file" relationship from the commit to each of 422 files. Relationships of this type had the
highest expansion weight. As a result, the entire repository was reachable from any point in two
steps, and random files filled the budget. The fix: expansion no longer traverses these
relationships from commits.

**Second defect: traversal against the direction of impact.** Relationships point from a dependent
item to what it relies on: "test checks code," "code depends on module." But traversal was
undirected — meaning half the search went not in the direction in which impact spreads, but the
opposite way: toward shared models, enums, and error handlers that are almost never the answer.
The fix: traverse dependency relationships in reverse.

Both fixes improved the hybrid's F1: **0.202 → 0.224 → 0.233**. The ceiling stayed put.

**We tested the nature of the relationships themselves.** A suspicion arose: perhaps code import
produces the wrong relationships? It tells us "module A uses module B," when what we need is
"A and B change together." We rebuilt the graph from files changed together in git history, with
proper safeguards against biasing the result. It performed **worse**: 0.212 versus 0.233.

### Why this happened

| graph configuration | recall |
|---|---|
| provenance star | 0.283 |
| star excluded | 0.283 |
| directed traversal + dampening | 0.292 |
| co-change graph | 0.283 |
| the same graph with equalized weights | 0.283 |
| **no graph at all** | **0.381** |

Five configurations. We changed edge types, traversal direction, weights, and hub handling — the
**mix of noise within the budget** changed, but the number of correct answers found did not.

The cause turned out to be the mechanics, not the quality of the relationships. It deserves a
separate explanation because it is not obvious and seems fairly general:

> **Under a fixed budget, graph expansion competes with search for the same slots.**
> There are roughly thirty slots. Every neighbor the graph adds to the package displaces someone
> else — specifically, a result from ordinary search. To at least break even, that neighbor has to
> be a correct answer itself. It almost never is.

The breakdown supports this by showing the opposite pattern. In the 15 cases involving Python code
changes, where the graph is active, **ordinary search** leads (0.220 versus 0.185). In the 8 cases
involving documents, CI, and frontend changes, where there are almost no relationships, the hybrid
leads (0.359 versus 0.261) — and it is ordinary word matching, not the graph, that carries it there.

In other words, the graph helps precisely where it isn't present.

---

## 6. Second test: does project intent exist only in AI conversations?

After the first defeat, the project turned to the subproblem that had never been tested at all:
No. 2 in the opening table — earlier agreements get lost.

### The claim

> Reasoning from AI development sessions contains decisions, rationales, and rejected alternatives
> that appear neither in code, nor in documentation, nor in commit messages. Engram can capture
> them with precise provenance and provide them to an agent.

It sounds plausible: you spent an hour discussing with the model why you chose PostgreSQL rather
than a graph database, and nothing of that conversation survived in the code except the choice
itself.

### The refutation criterion — declared BEFORE measurement

This detail matters, and the reason will become clear below.

> If the share of annotated project decisions whose rationale or rejected alternatives are
> recorded **only** in a transcript is below **30%**, the claim is considered refuted: commits
> and documentation already fill this niche, and this line of work is closed.

### How it was measured

We took **29 project decisions** from architectural documents, ADRs, instructions, the roadmap, and
commit subjects. The list was **frozen before opening a single transcript**. This is the main
safeguard against self-deception: if you compile a list of decisions while reading conversations,
the share found "only in a conversation" will be high simply by construction.

Each decision was annotated along three independent axes: where its **conclusion** was recorded,
where its **rationale** was recorded, and where its **rejected alternatives** were recorded.
Possible answers: code, ADR, document, commit, transcript, nowhere. Annotation took two passes, and
their order was essential:

1. **First pass — repository only.** Search code, documents, and commits. Commit the annotations
   **before** opening the first transcript.
2. **Second pass — transcripts.** Only now look at the conversations.

This order prevents tailoring the result: the decision about whether a rationale exists in the
repository is made without knowing what the conversation contains. Every label required a citation
— a file and line, a commit, or a range of messages — so that anyone could verify it rather than
take it on trust.

### Results

**1 decision out of 29. That is 3.4% against a 30% threshold. The claim is refuted.**

Where this project's knowledge actually ends up:

| axis | code | ADR | document | commit | transcript | nowhere |
|---|---|---|---|---|---|---|
| conclusion | 69% | 52% | **100%** | 24% | 0% | 0% |
| rationale | 17% | 24% | **86%** | 24% | 10% | 3% |
| alternatives | 3% | 7% | **62%** | 14% | 0% | 24% |

The outcome was already determined by the first pass: searching the repository alone left a gap
for just seven decisions out of 29, putting the ceiling at 24.1% — already below the threshold,
whatever the conversations contained. The second pass resolved one of those seven.

The sole match was the rule "for every data-model change, write a migration and test it both on
existing data and on a clean installation." The rule itself is recorded in the project
instructions, but the **reason** appears nowhere except in a conversation from August 1. It
explains that the full migration cycle must be run because the migration converts old data to a new
format and adds required fields.

An additional irony: that sole fragment is in a Codex transcript, while the importer that motivated
the whole effort would, under the adopted decision, parse only the Claude Code format. So the
mechanism wouldn't have captured even the one piece we found.

### Why this happened

The cause had been identified in advance in the list of biases, and it proved decisive: **this
project is unusually thoroughly documented.** The main planning document, 726 lines long, gives the
problem and rationale behind almost every architectural choice. Commit messages contain
paragraphs of reasoning — one explains a discovered defect, its fix, the measurement, and
separately withdraws an unsupported speed claim.

The niche targeted by the claim was already occupied. But it was occupied **in this project** —
there is no basis for a broader claim.

---

## 7. Third test: uncovering our own self-deception

After two defeats, one result remained that the project considered firmly established and had
reported in three documents:

> Bounded, explained selection beats full context by a wide margin: F1 of 0.233 versus 0.048.

The interpretation was: "we have proved that selecting context is better than dumping everything
in." The entire justification for the project rested on this.

**The claim turned out to be false.** When we revisited the experimental setup, we found that the
`full` control worked as follows: every item received a score of `1.0`, meaning **all items were
equal**, there was no ranking, and the budget simply truncated the list.

Checking the saved results showed that:

- across all 23 cases and both repeats, the method returned **the same set of 17 paths**;
- these were simply the first files in the repository in alphabetical order:
  `.claude/agents/frontend-architect.md`, `Claude.md`, `DESIGN.md`…;
- token usage was exactly 5994 in all 46 rows, without exception.

In other words, the control **did not depend on the question**. It gave the same answer to every
change.

So "0.233 versus 0.048" literally means: **ranked search is better than answering every question
with the same seventeen files.** That is a code sanity check, not evidence for context selection.

The claim was removed from all documents, and both results tables were annotated so that the
`full` row could not be read as a baseline without the surrounding explanation.

**After that, the project had no measured advantage left.** The roadmap records this in exactly
those terms.

---

## 8. Fourth test: halted

Once it became clear that no genuine control comparison had been performed, we registered one and
attempted it: give a **real model** the same 23 cases twice — once with the entire corpus, once
with an Engram package of 6000 tokens — and compare which files it names.

The measurement was **halted after 3 successful calls out of 92**, for two reasons.

**First, we hit a physical limit.** The project's corpus contains 146 files, 805,439 characters,
or roughly 201 thousand tokens. The model's context window is 200 thousand. It doesn't fit. A
second barrier appeared immediately: the subscription quota supports roughly one such call per
quota-recovery window, while we needed 46. That means days of elapsed time.

**The second reason matters more.** The baseline turned out to be a straw man. Dumping 176 thousand
tokens of raw repository text into a model is not how any actual agent works. The real competitor
Engram must be compared against is **an agent with file search** — ordinary Claude Code doing its
everyday work. It appeared in none of the project's experiments. Beating a dump would tell us
nothing about the product's value.

This test also forced us to withdraw another claim of our own. Initially, we had recorded a channel
ceiling of 125–150 thousand tokens, supposedly "below the model's context window." It turned out
that the probes had run in ascending order of size, and the failure was quota exhaustion, not a
size limit. After the quota recovered, both 150k and 175k went through. The actual boundary is the
model's context window, as expected. The conclusion was corrected.

The only substantive data point is reported as an observation, not a result: on one case, a
6000-token package identified 5 correct files out of 5, while a 176,000-token dump identified the
same 5 correct files plus 7 unnecessary ones. One case proves nothing.

---

## 9. Conclusions

### What has been built and works

The system exists. Provenance, item-level versioning, non-mutating analysis, mandatory human
review, reproducible packages with a hard budget, read-only GitHub import, a delivery channel for
an external agent, 58 tests against a real database, passing CI. This is not a mock-up.

One point deserves special mention: when we needed to introduce a fundamentally new knowledge
source that had not been anticipated (AI conversations), it **fit the existing data model without
a single schema change**. This independently confirms that the architectural decisions were sound.

### What was tested and not confirmed

| Claim | How it was tested | Outcome |
|---|---|---|
| A relationship graph improves context selection | 23 cases, 5 graph configurations, each run twice | **Refuted.** Tied with ordinary search on F1, worse recall |
| Project intent exists only in AI conversations | 29 decisions, list frozen in advance, two-pass annotation | **Refuted.** 3.4% against a 30% threshold |
| Bounded selection beats full context | review of our own control | **Withdrawn.** The control was degenerate |
| A package is cheaper than investigating independently | attempted measurement | **Halted.** The baseline turned out to be a straw man |

### The main conclusion, stated exactly as the numbers warrant

**The problem was correctly framed, and the requirements for provenance, versioning, and
non-mutation were sound — all of this has been built and works. The bets on specific mechanisms
were wrong.**

But there is an important caveat, without which the conclusion would be stronger than the numbers
support. All three negative results came from **a single repository**: 146 files, 31 commits,
unusually detailed documentation, and a corpus that almost fits in the model's context window in
its entirety.

This is **the worst possible testbed** for a context-management tool. Here, the agent simply
doesn't face the problem Engram solves: it can read almost the entire project and find anything
with ordinary search.

The honest formulation is therefore:

> An advantage **cannot be demonstrated on the corpus that was available**. A corpus where it
> would make sense to look for one — a large project with a real issue tracker and poorly
> maintained documentation — is beyond the budget of this work.

That is not the same as "the product is unnecessary." But neither is it the same as "the product
is useful." The latter has not been proved and cannot be claimed.

---

## 10. What the process itself taught us

These lessons cost the most and are perhaps more useful than any of the measurements.

**Small samples mislead.** The first run used 10 cases. The hybrid came first by a margin of 0.012,
and we published that as confirmation of the hypothesis. Expanding the dataset to 23 reversed the
ranking. The conclusion had to be withdrawn.

**Hence the rule: declare the criterion before measuring.** Both subsequent measurements followed
this procedure: first, record in a separate commit what result would count as refutation; only
then run the measurement. The order is visible in git history, not merely asserted. This is not a
formality — it is the only thing that prevents tailoring the conclusion to the number obtained.

**Scrutinize the control as closely as the main method.** A degenerate control masqueraded as the
project's main achievement for a month and a half. Nobody checked that it gave the same answer to
every question.

**Reproducibility requires repeats.** A single run cannot reveal a failure to reproduce: there is
nothing to compare it with, so the metric trivially reports zero discrepancies. All measurements
were run twice, and absolute counts were taken from the first run so that repeats would not double
them.

**Speed claims require controls.** Once, a speedup was attributed to a code fix. We checked:
timings on this machine vary by a factor of three to four between runs with bit-for-bit identical
output. The claim was withdrawn.

**A negative result with an identified mechanism is still a result.** "It didn't work" is not a
result. "It doesn't work, and here is why: under a fixed budget, expansion competes with search for
the same thirty slots" is a result, and it can be reused.

---

## 11. Technical details

### Repository layout

```text
apps/api/      FastAPI, domain logic, migrations, and tests
apps/web/      Next.js and the generated API client
infra/         PostgreSQL + pgvector for development
docs/adr/      Architectural decisions
research/      Reference dataset, measurement results, and methods
scripts/       Import, experiments, and utilities
```

Key documents for more detail:

- [`research/RESULTS.md`](research/RESULTS.md) — full figures from the first experiment;
- [`research/DECISION_PROVENANCE.md`](research/DECISION_PROVENANCE.md) — method and results of the
  second test;
- [`ENGRAM_TRUE_PATH_PLAN.md`](ENGRAM_TRUE_PATH_PLAN.md) and
  [`ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md`](ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md) — the problem statement
  and all revisions;
- [`docs/adr/`](docs/adr/) — adopted decisions, including one overturned by its own criterion;
- [`ROADMAP.md`](ROADMAP.md) — stages and their status.

### Running the project

You need Python 3.11+, Node.js 22+, pnpm 11, Docker, and Docker Compose.

```bash
docker compose -f infra/docker-compose.yml up -d

cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn engram.main:app --reload

# in another terminal, from the repository root
pnpm install
pnpm web:dev
```

The API will be available at <http://localhost:8000>, and the web app at <http://localhost:3000>.

You can retrieve an approved context package through the API or the dependency-free CLI:

```bash
python scripts/engram_context.py --project <uuid> --analysis <uuid> --budget 4000
python scripts/engram_context.py --project <uuid> --package <uuid>
```

### Channel for an external AI agent

An MCP-capable agent can initiate analysis and retrieve a package itself:

```bash
cd apps/api && uv sync --extra mcp
claude mcp add engram -- uv --directory apps/api run python -m engram.mcp.server
```

Available operations: `list_projects`, `analyze_change`, `get_context`, `list_context_packages`.
Candidate confirmation is **deliberately unavailable** to the agent — impact approval is the human
decision around which the whole workflow is built, so `get_context` will refuse until review is
complete.

### Checks

Automated tests always use deterministic model mocks, regardless of the developer's local settings.

```bash
cd apps/api
ENGRAM_LLM_PROVIDER=mock uv run pytest
uv run ruff check .

cd ../..
pnpm --filter @engram/web exec eslint .
pnpm --filter @engram/web exec next build
```

### Reproducing the experiments

```bash
# first experiment: four context-selection methods
ENGRAM_EMBEDDING_PROVIDER=local ENGRAM_LLM_PROVIDER=mock uv run uvicorn engram.main:app
python scripts/link_python_imports.py <project_uuid> <revision_uuid>
python scripts/run_retrieval_experiment.py --project <project_uuid> \
    --budget 6000 --max-candidates 30 --repeats 2
python scripts/evaluate_retrieval.py research/benchmark_cases.json research/results.json

# second test: where decision rationales are recorded
python scripts/count_decision_provenance.py research/decision_provenance.json
```

### Product boundaries

Engram does **not** replace GitHub, an issue tracker, or a documentation editor. External systems
remain the source of truth. Engram indexes them, connects them, explains them, and provides bounded
context. It does not apply model suggestions or write anything back to the repository.

Frozen until at least one claim of value has been confirmed: authentication and roles,
collaboration, additional integrations, automatic fixes, Neo4j, LangGraph, and visual polish.
The list and reasons are in [`FROZEN_IDEAS.md`](FROZEN_IDEAS.md).
