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
