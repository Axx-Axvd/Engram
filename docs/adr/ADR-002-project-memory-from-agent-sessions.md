# ADR-002: Project memory is captured from agent sessions

- Status: accepted
- Date: 2026-08-10
- Amends: [ADR-001](ADR-001-product-boundary.md) (not superseded)

## Context

ADR-001 committed Engram to being a change-impact layer whose primary output is an evidence-backed
impact analysis and a bounded context package, and stated that product readiness would be decided by
comparative measurement rather than feature count. That measurement has now been made.

On a 23-change gold set, run twice per case against the Engram repository pinned at `18e3162`, the
typed graph did **not** improve context selection. The hybrid ties plain semantic retrieval on F1
(0.2332 vs 0.2331) and loses recall (0.292 vs 0.381); it wins only precision and false-warning count.
Two structural defects were found and fixed by measurement — a commit provenance star and undirected
expansion — lifting the hybrid from F1 0.202 to 0.233 without moving the recall ceiling. Rebuilding
the graph from co-change edges mined from git history, the most direct test of "the edge type is
wrong", did worse (0.212), under a setup biased in its favour.

Across five graph configurations, recall stayed at 0.283–0.292 while retrieval without any graph
reached 0.381. Changing edge type, direction, weight and hub handling changed which wrong items
entered the budget, not how many right ones were found. Under a fixed budget, expansion competes with
retrieval for the same slots, and a neighbour that displaces a correct hit must itself be correct to
break even. Details: [`research/RESULTS.md`](../../research/RESULTS.md).

Meanwhile the original specification lists six sources of value, of which only "better change
analysis" was ever measured. Two remain untested: preserving knowledge **between steps and sessions**,
and context/token economy. Its second stated sub-problem is that "old agreements get lost", and its
working title was "a project memory layer for long AI projects".

## Decision

The primary source of value becomes **rationale captured from AI development sessions**.

An agent session is a source in exactly the same sense as a repository: the session is a
`SourceRevision`, a range of messages is a `SourceLocator`, an extracted decision is a versioned item
of type `decision`, and files edited within the same session segment are linked to it as
`code_component --implements--> decision`. No schema migration is required, which is independent
confirmation that the provenance model of ADR-001 was designed correctly.

Raw session messages are never persisted. Only the extracted decision text is stored, together with
the locator that lets a human verify it against the original transcript.

Rationale is served by a direct link lookup, not by the scoring and expansion pipeline. The pipeline
was measured and does not help selection; here the graph does not compete with search, it supplies an
answer search cannot give, because code does not state which decision it implements.

The claim is falsifiable and its kill criterion is registered before the measurement: if fewer than
30% of the project's decisions have their rationale or rejected alternatives recorded **only** in a
transcript, the direction is closed and the result recorded.

## Consequences

- Impact analysis, candidate review, ChangeSet import and the GitHub adapter are retained unchanged,
  but impact analysis is no longer what Engram calls itself.
- The typed graph keeps its measured property — a third fewer false warnings at equal budget — and
  loses its claim to improving retrieval. That claim is removed from all project documents.
- Further tuning of edge weights and types for retrieval metrics is frozen. It becomes worthwhile
  again only if the budget mechanics change: a reserved quota for expansion, or admitting a neighbour
  only when it also has semantic support.
- Session ingestion must segment a session before extracting, and must degrade a wide-fan-out segment
  to `proposed` links. An unsegmented session would recreate the provenance star this measurement
  already exposed once.
- Extraction uses the LLM provider abstraction with the same atomic-rejection discipline as impact
  analysis: a decision citing a message range that does not exist rejects the whole segment.
- Secrets are a first-class concern for this source in a way they were not for GitHub: a session can
  contain tokens a developer pasted. Storing only extracted text is a design constraint, not a
  preference.
- ADR-001 remains in force for product boundary, non-mutation, human review and provenance.
