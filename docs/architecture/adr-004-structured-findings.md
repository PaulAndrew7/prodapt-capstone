# ADR 004: Structured findings plus deterministic checks

Status: Accepted  
Date: 2026-09-26

## Context

The panel must be able to trace every conclusion to a clause. Prose answers hide which requirement was checked and which facts were used.

## Options

- **Prose response with citations appended.** Cheap; unverifiable.
- **Typed findings: requirement, status, facts, citations, support.** More schema work; every claim is checkable.

## Decision

Assessments are the typed `Assessment` contract (`app/domain/contracts.py`). Requirement status, evidence support, risk and human review are separate fields. Citations are built by the backend from stored clause rows; models may only select allowed IDs. Explicit thresholds run in an allowlisted rule interpreter, never `eval`.

## Consequences

More schema and validation code; model outputs need structured-output validation and a repair path.

## Revisit when

None expected. This is a core product invariant.
