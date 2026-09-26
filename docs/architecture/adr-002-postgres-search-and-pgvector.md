# ADR 002: Postgres full-text search and pgvector in one database

Status: Accepted  
Date: 2026-09-26

## Context

Retrieval needs lexical and dense channels over about 10,000 chunks, with the same authorization, snapshot and effective-date filters, and transactional consistency with policy versions.

## Options

- **Dedicated search engine plus vector database.** Better ranking features; two more services to run, sync and secure; filters duplicated.
- **Postgres `tsvector` + pgvector in the application database.** One store, one transaction, identical filters for both channels.

## Decision

Store chunks in Postgres with a generated, weighted `tsvector` (clause path A, body B) and a `vector(384)` embedding. Start with exact vector scans (no HNSW) because approximate indexes can drop filtered candidates; benchmark before adding an index.

## Consequences

Fewer ranking knobs than a search engine. `ts_rank_cd` is not BM25 and must not be described as BM25.

## Revisit when

Held-out retrieval evaluation misses Recall@10 targets after tuning, or p95 search latency exceeds its budget at the demo corpus size.
