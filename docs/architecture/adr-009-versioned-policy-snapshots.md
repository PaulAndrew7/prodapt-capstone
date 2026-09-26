# ADR 009: Versioned policy snapshots

Status: Accepted  
Date: 2026-09-26

## Context

Policies change. A historical assessment must keep resolving the exact text it cited after a newer version is published.

## Options

- **Always query the latest documents.** Simple; history silently changes meaning.
- **Immutable versions and snapshots.** More storage and logic; reproducible results.

## Decision

Policy versions are immutable once ingested (different bytes under an existing label are rejected). A `policy_snapshot` pins an explicit set of versions and index revisions; every run records its snapshot. Citations reference versions and clauses with `ON DELETE RESTRICT`. Retrieval filters by snapshot and by the scenario's as-of date against effective ranges.

## Consequences

Old versions and their chunks are retained while any retained assessment cites them.

## Revisit when

None expected. Required for interpretable historical results.
