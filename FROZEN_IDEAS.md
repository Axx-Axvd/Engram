# Frozen ideas

These ideas are intentionally outside active development until one claim about Engram's value has
been measured and held (see [`ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md`](ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md)
and [`docs/adr/ADR-002`](docs/adr/ADR-002-project-memory-from-agent-sessions.md)):

- **tuning graph weights or edge types to improve retrieval metrics.** Five configurations were
  measured, including co-change edges mined from git history; recall stayed at 0.283–0.292 against
  0.381 with no graph at all. The limit is the fixed budget, where expansion competes with retrieval.
  This becomes worthwhile again only if the budget mechanics change — a reserved quota for expansion,
  or admitting a neighbour only when it also has semantic support;
- **ingesting agent sessions as a source of rationale.** Closed by measurement rather than deferred:
  of 29 decisions of this project, frozen before any transcript was opened, exactly one has its
  rationale recorded only in a session — 3.4% against a 30% threshold registered in advance, and that
  one sits in a transcript format the importer was scoped not to read. 86% have their rationale in a
  repository document. Reopening this needs a project whose rationale demonstrably does not reach its
  documents, measured the same way first, not assumed. See
  [`research/DECISION_PROVENANCE.md`](research/DECISION_PROVENANCE.md);
- **staleness tracking for documentation as a product value.** Code is always current with respect to
  itself, so this only bites on derived knowledge, where it is worth little to an agent. The
  direction that would have mattered — "the decision changed, and here is the code implementing the
  old one" — depended on the rationale store above and closes with it;
- further rich-text editor features and bidirectional content/items synchronisation;
- comments, notifications, real-time collaboration, users, roles and permissions;
- visual redesign, advanced graph layout and animation;
- automatic consistency repair or automatic application of LLM suggestions;
- Jira, Confluence, Notion, Slack and additional model integrations;
- DOCX/PDF export and UML generation;
- Neo4j, LangGraph and multi-agent orchestration;
- production platform work beyond what the research deployment requires.

The existing editor, graph, formalization flow and Claude provider remain available for
compatibility and demonstrations, but receive defect fixes only.
