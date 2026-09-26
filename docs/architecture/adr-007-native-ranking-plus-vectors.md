# ADR 007: Native text ranking plus vectors, fused by RRF

Status: Accepted  
Date: 2026-09-26

## Context

Policy questions mix exact terms ("data owner", "14 days") with paraphrase ("send records to a vendor").

## Options

- **Dense only.** Misses exact terms and numbers.
- **Lexical only.** Misses paraphrase.
- **BM25 extension or external engine.** Another dependency before a measured need.

## Decision

Run lexical (`to_tsquery` over the question's lexemes, OR-combined, ranked with `ts_rank_cd`) and dense (cosine, bge-small-en-v1.5 via fastembed ONNX) channels with identical filters; take the top 20 of each and fuse with reciprocal rank fusion, k = 60; keep the best chunk per clause. Scores are ranking heuristics, never probabilities.

## Consequences

Postgres lexical ranking has known limitations versus BM25.

## Revisit when

An ablation on the held-out set shows a measurable gap that a different lexical ranker closes.
