# Where is a decision's rationale recorded?

The premise check for project memory, stage 8 of [`ROADMAP.md`](../ROADMAP.md) and stage 0 of
[`ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md`](../ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md).

**This document is committed in two parts. Everything below is the method, and it is committed
before a single label is written and before any transcript is opened.** The result is appended
afterwards, in a separate commit. The order is visible in `git log` rather than merely asserted,
because the one previous conclusion drawn the other way round — "the hybrid wins", published on ten
cases — was reversed at twenty-three.

## The claim under test

Reasoning from AI development sessions contains decisions, justifications and rejected alternatives
that reach neither the code nor the documentation nor the commit messages.

## Kill criterion, registered in advance

If the share of the project's decisions whose **rationale or rejected alternatives** are recorded
**only** in a session transcript is below **30%**, the claim is refuted, the niche is already
occupied by commits and documentation, and the direction closes with the result recorded.

The share is reported as two numbers, both declared here:

- **Primary (conditional).** Denominator: decisions for which a transcript physically survives. The
  30% threshold is attached to this number, because it measures the claim rather than the
  completeness of an archive.
- **Secondary (unconditional).** Denominator: every labelled decision. No threshold is attached, but
  it is published alongside, because omitting it would make the primary number look better than the
  evidence is. Eleven of this project's thirty-one commits have no transcript at all; see §23.3 of
  the addendum.

A third number is reported for the same reason: the share of "only in a transcript" decisions whose
transcript is in a format the stage-9 importer can actually read. The importer parses Claude Code
sessions only, while much of the corpus is Codex rollouts, and the gap between those two numbers is
the honest measure of how much work the gate defers rather than removes.

## The population is frozen before any transcript is opened

The list of decisions is drawn **only** from specification sources: `docs/adr/ADR-001`,
`docs/adr/ADR-002`, `ENGRAM_TRUE_PATH_PLAN.md` §6–§10, `ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md`,
`CLAUDE.md`, `ROADMAP.md`, `FROZEN_IDEAS.md`, and commit subjects. It is written to
[`decision_provenance.json`](decision_provenance.json) and committed **before** the first
transcript is read.

This is the central anti-selection device. A list assembled while reading transcripts would score
high on "only in a transcript" by construction — that is the same defect that produced the retracted
ten-case conclusion, and freezing the list is the only defence against it.

Admission rule: a statement enters the population if it **constrains future work** — it forbids
something, fixes a boundary, or picks one mechanism over others. Descriptions of what exists are not
decisions and are excluded.

## Three independent axes

For each decision, three separate questions, each answered with the same value set:

| Axis | Question |
|---|---|
| `conclusion_in` | Where is the **outcome** stated? |
| `rationale_in` | Where is the **reason** stated? |
| `alternatives_in` | Where are the **rejected options** named? |

Values: `code`, `adr`, `doc`, `commit`, `transcript`, `nowhere`.

- `code` — source files, including docstrings and comments, and tests that encode the rule.
- `adr` — anything under `docs/adr/`.
- `doc` — any other repository document: `README.md`, `ROADMAP.md`, `CLAUDE.md`, `FROZEN_IDEAS.md`,
  the plan documents, `research/`.
- `commit` — a commit subject or body.
- `transcript` — an agent session transcript, Claude Code or Codex.
- `nowhere` — none of the above, after a recorded search.

An axis may hold several values. `nowhere` is exclusive with the rest.

## Labelling protocol

**Every non-`nowhere` value requires a citation** — `path:line`, a commit sha, or a session id with
a message range — so that each label can be checked instead of trusted. Every `nowhere` requires the
search terms used, recorded in the entry.

Two passes, in this order, and the order matters:

1. **Pass 1 — repository only.** For every decision, search code, ADRs, documents and commit
   messages. Fill `conclusion_in`, `rationale_in` and `alternatives_in` with everything found there.
   Commit this pass before opening any transcript.
2. **Pass 2 — transcripts.** Only now open the session transcripts and add the `transcript` value
   where the rationale or the alternatives are found.

Pass 1 decides whether the repository holds the rationale. Running it first makes that judgement
impossible to shade with knowledge of what the transcript contains — and it is exactly the judgement
that determines the numerator, since "only in a transcript" means *absent from code, ADR, doc and
commit*.

Labels are produced by the agent, with a citation on every value, and disputed entries are settled
by the project owner. The citations exist so that disagreement is possible.

## Dates and transcript availability

Each entry records the dates at which the decision was introduced or restated in the repository,
taken from `git log` rather than from memory. `transcript_available` is true when a surviving
transcript's window covers **any** of those dates, per the coverage table in §23.3 of the addendum.

This rule is deliberately generous: a decision first made in an untranscribed session but
re-deliberated in a transcribed one counts as available. It is declared here as a bias in favour of
the claim.

## Declared biases

Against the claim:

- **Commit messages in this repository are unusually detailed**, several paragraphs of reasoning
  each. Where a rationale reached a commit body, it is by definition not "only in a transcript".
- **The ADR-002-era decisions were documented immediately**, in the addendum and in the ADR, in the
  same week they were taken. Their rationale is in a document by construction.

In favour of the claim:

- **The 9–12 August window is research work**, where deliberation is denser than in ordinary
  implementation, and it is also the best-transcribed window.
- **The availability rule above** resolves ambiguous dates towards "a transcript exists".
- **Decisions taken in the very sessions being labelled** are part of the population. The result is
  therefore reported broken down by period, so the recent decisions can be inspected separately.

Both directions are present and neither is obviously dominant, which is why the result is reported
with the breakdown rather than as a single number.

## Corpus

The transcripts available for pass 2, fixed here so that none can be added later to move a number:

| Store | Sessions | Covers |
|---|---|---|
| Claude Code | `85d60c24`, `58da506d`, `18ea9dcb` | 9–12 August |
| Codex | 4 rollouts 28–29 May, 1 rollout 1 August, 1 rollout 9 August | 28–29 May, 1 August, 9 August |

Not covered: 26–27 May, eleven commits, the entire foundation of the project — the monorepo
scaffold, the artifact domain with versioning and links, embeddings and retrieval, the formalization
workflow and the web shell.

## Reproducing the count

```bash
python scripts/count_decision_provenance.py research/decision_provenance.json
```

---

# Result

**The claim is refuted. The direction closes.**

| | |
|---|---|
| Decisions in the frozen population | 29 |
| Rationale or rejected alternatives **only** in a transcript, conditional | **1/29 = 3.4%** |
| Same, unconditional | 1/29 = 3.4% |
| Registered threshold | 30% |
| Of those, readable by the planned Claude Code importer | **0/1 = 0%** |

The measured share is an order of magnitude below the registered threshold. This is not a
borderline result that better labelling could move.

## Where the project's rationale actually lives

| | `code` | `adr` | `doc` | `commit` | `transcript` | `nowhere` |
|---|---|---|---|---|---|---|
| conclusion | 69% | 52% | 100% | 24% | 0% | 0% |
| rationale | 17% | 24% | 86% | 24% | 10% | 3% |
| alternatives | 3% | 7% | 62% | 14% | 0% | 24% |

Every decision's outcome is written down somewhere, and 86% have their reasoning in a repository
document. The transcript adds essentially nothing the repository does not already hold.

## The outcome was fixed before the transcripts were opened

Pass 1 searched the repository alone and found only seven decisions with any gap: D-04, D-13, D-18,
D-19, D-20, D-21 and D-28. Those seven were the entire set pass 2 could still move, so the share
could not have exceeded 7/29 = 24.1% — already below the threshold — whatever the sessions
contained. That ceiling is visible in commit `017e8b0`, which is the pass-1 commit, made before any
transcript was read.

Pass 2 then moved exactly one of the seven.

## The single hit, and how fragile it is

**D-19** — "every model change ships with an Alembic migration tested on both existing data and
clean installs." `CLAUDE.md:77` states the rule. Nothing in the repository states the reason: the
migration file `c41f0e9a2b11_true_path_domain_model.py` carries no explanatory docstring, and the
rule is never argued. The reason appears once, in a Codex rollout of 1 August, message 213: the full
lifecycle must be exercised on a temporary database *because that migration moves legacy JSONB data
into normalised items and adds mandatory project and provenance columns*.

It is also the weakest label in the set. A stricter reading that counted `ROADMAP.md:42` — "migrate
existing data into a default project without loss" — as a stated reason rather than a delivery
requirement would move D-19 to `doc` and make the result **0/29**. The gate fails either way, which
is why the judgement is recorded here rather than argued.

And the one surviving fragment is in a **Codex** rollout, which the stage-9 importer was scoped not
to read. The mechanism the gate was protecting would not have captured the only thing the gate
found.

## What the two denominators did, and did not, do

They coincided. Under the availability rule registered in advance — a transcript covering *any* date
at which a decision was introduced or restated — all 29 decisions count as covered, because the
1 August true-path plan and the 9 August implementation restated nearly every foundational decision,
and both days are transcribed. The eleven untranscribed commits of 26–27 May therefore did not
distort anything, and the caveat that motivated the two numbers turned out not to bite.

Computed afterwards, and reported here only for transparency rather than as a registered criterion:
by *first* appearance, four decisions originate on 26–27 May with no transcript, and the one hit
(D-19, first seen 26 May) is among them. Under that stricter reading the conditional share would be
1/25 = 4.0%. The conclusion does not change.

## Why the repository holds so much

The bias declared in advance is the explanation, and it was decisive:

- `ENGRAM_TRUE_PATH_PLAN.md` §5 states a problem, a justification and a decision for nearly every
  architectural choice — it is 726 lines of recorded deliberation.
- Commit bodies carry paragraphs of reasoning. `e5ca3c5` and `53dedc1` explain a retrieval defect,
  the fix, the measurement and an explicitly retracted speed claim, in the commit itself.
- The project was audited twice, and both audits were written up as documents rather than left in
  the sessions that produced them.

That is a property of this project, not a refutation of the underlying intuition. What the numbers
support is narrow and should be stated narrowly: **in this repository, on this population of 29
decisions, rationale is recorded outside the transcript almost without exception.** Whether a
project that does not write plan documents and paragraph-long commits would look different is not
measured here and must not be claimed.

## Conflicts of interest, stated

The labels were produced by the same agent that wrote ADR-002, the addendum and this method, in the
same week. Five of the 29 decisions (D-24 to D-27, D-23) were taken in the sessions being labelled.
That is why every value carries a citation: the labels are checkable, and disagreement with any of
them is possible without re-running anything. It cuts against the claim rather than for it, since
those five decisions were documented immediately and so score as `doc`.

## Consequence

Per §27 of the addendum this is a registered outcome, not a surprise: the direction is recorded as
the project's **second measured negative result** and closed. Stages 9 and 10a of `ROADMAP.md` —
agent sessions as a source, and the decision-adherence measurement — are not built.

What survives is §25.2, the auxiliary engineering claim: whether a prepared context package brings
an agent to the same outcome in fewer tokens and steps than its own exploration. It is the only
remaining measurable statement about Engram's value, it is stated as an engineering property with no
claim to novelty, and the machinery it needs — the MCP channel, the 23-case gold set, the package
CLI — already exists.

The by-product is worth keeping: `decision_provenance.json` is a citation-backed map of where all 29
of this project's decisions are recorded, which is useful independently of the claim it failed to
support.
