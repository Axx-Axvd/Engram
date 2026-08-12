# Frozen ideas

These ideas are intentionally outside active development until one claim about Engram's value has
been measured and held (see [`ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md`](ENGRAM_TRUE_PATH_PLAN_ADDENDUM.md)
and [`docs/adr/ADR-002`](docs/adr/ADR-002-project-memory-from-agent-sessions.md)):

- **tuning graph weights or edge types to improve retrieval metrics.** Five configurations were
  measured, including co-change edges mined from git history; recall stayed at 0.283–0.292 against
  0.381 with no graph at all. The limit is the fixed budget, where expansion competes with retrieval.
  This becomes worthwhile again only if the budget mechanics change — a reserved quota for expansion,
  or admitting a neighbour only when it also has semantic support;
- **staleness tracking for documentation as a product value.** Code is always current with respect to
  itself, so this only bites on derived knowledge, where it is worth little to an agent. The
  direction that does matter — "the decision changed, and here is the code implementing the old
  one" — belongs to the addendum's claim, not to a separate effort;
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
