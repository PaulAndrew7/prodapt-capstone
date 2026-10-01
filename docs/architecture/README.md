# Architecture decision records

> Scope update, 26 September 2026: the revised [implementation plan](../../IMPLEMENTATION_PLAN.md) governs the submission. The records below document earlier decisions; their original statuses are retained as history. The separate worker in ADR 001 and graph/repair workflow in ADR 003 are superseded for this release by an in-process task and ordinary Python functions. ADR 004 does not require a general rule interpreter. ADR 006 retains HTTP/SSE progress without a replay platform, ADR 005 is optional polish, and ADR 009 retains version references without policy-change impact features. These are planning changes, not claims that implementation has been completed.

**Start here:** [decisions.md](decisions.md) describes the decisions and tradeoffs of the code as submitted. The architecture diagram is [architecture.pdf](architecture.pdf) (also as [system](architecture-system.jpg) and [workflow](architecture-workflow.jpg) JPEGs), exported from the editable [diagram/architecture.html](diagram/architecture.html) with `corepack pnpm --dir apps/web export:architecture`. A shortened version with simpler wording is [architecture-short.pdf](architecture-short.pdf) ([system](architecture-short-system.jpg), [workflow](architecture-short-workflow.jpg)), from [diagram/architecture-short.html](diagram/architecture-short.html).

Recorded 2026-09-26 during F00. Each record states context, options, decision, cost and the evidence that would change it.

| ADR | Decision | Original status | In the submitted code |
|---|---|---|---|
| [001](adr-001-one-backend-codebase.md) | One backend codebase with API and worker processes | Accepted | One codebase kept; the worker became an in-process background task |
| [002](adr-002-postgres-search-and-pgvector.md) | Postgres full-text search and pgvector in one database | Accepted | As recorded |
| [003](adr-003-explicit-graph-bounded-calls.md) | Explicit workflow graph with bounded model calls | Accepted | Bounded calls kept; the graph and retrieval-repair loop became a fixed sequence of functions |
| [004](adr-004-structured-findings.md) | Structured findings plus deterministic checks | Accepted | As recorded, without a general rule interpreter |
| [005](adr-005-local-reactive-avatar.md) | Local reactive avatar | Accepted | Mirrors real run states; optional |
| [006](adr-006-http-and-sse.md) | HTTP for actions, Server-Sent Events for run progress | Accepted | As recorded; reconnect replays saved events, no replay platform |
| [007](adr-007-native-ranking-plus-vectors.md) | Native text ranking plus vectors, fused by RRF | Accepted | As recorded; measured on dev data |
| [008](adr-008-typed-internal-a2a.md) | Typed internal agent messages; formal A2A protocol deferred | Proposed | Handoff records implemented; formal A2A not implemented |
| [009](adr-009-versioned-policy-snapshots.md) | Versioned policy snapshots | Accepted | Snapshots and effective dates used; policy-change impact deferred |
