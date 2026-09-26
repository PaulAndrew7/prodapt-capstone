# ADR 003: Explicit workflow graph with bounded model calls

Status: Accepted  
Date: 2026-09-26

## Context

Free-form multi-agent conversation is hard to test, can loop, and makes cost and latency unpredictable.

## Options

- **Open agent debate until consensus.** Flexible; unbounded cost; majority vote is not evidence.
- **Explicit graph with fixed stages and one repair loop.** Predictable, testable and replayable.

## Decision

Model the assessment as an explicit graph (retrieval → analysis → clarification? → risk → validation → one optional evidence repair → recommendation → evidence gate). Hard per-run budget of 8 model calls, one retrieval repair, one schema repair per stage, and a wall-clock deadline (`RUN_MAX_MODEL_CALLS`, `RUN_DEADLINE_SECONDS`).

## Consequences

Some open-ended questions will get a qualified answer instead of more exploration.

## Revisit when

A measured task category cannot be handled by the existing routes.
