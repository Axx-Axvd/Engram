# ADR-001: Engram is a change-impact layer

- Status: accepted
- Date: 2026-08-01

## Context

The prototype invested heavily in creating and editing documents inside Engram. That direction
duplicates established source systems while leaving the core hypothesis—reliable change-impact
analysis and minimal agent context—largely untested.

## Decision

External repositories, documents and work trackers remain sources of truth. Engram stores immutable
source revisions and a derived, versioned knowledge model. Its primary output is an evidence-backed
impact analysis and a bounded reproducible context package. Model suggestions are proposals and
must not modify source knowledge automatically.

Documents remain compatibility containers. The primary analysis unit is a versioned item with a
source locator. PostgreSQL and typed relational links remain the storage model; no separate graph
database or orchestration framework is introduced for the corrected MVP.

## Consequences

- Project isolation and provenance are correctness requirements, not future multi-user features.
- Rich-text authoring and general graph polish are frozen.
- GitHub is the first and only source adapter during MVP validation.
- Impact analysis, review, context delivery and ChangeSet import are separate operations.
- Product readiness is decided by comparative measurements, not feature count.
