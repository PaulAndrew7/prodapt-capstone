# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + TypeScript + Vite frontend (`apps/web`), FastAPI + Pydantic backend (`services/api`), PostgreSQL + pgvector, run locally from a Python package (`uv run python -m app.cli db-start`; Docker was dropped on 29 September). The five-role workflow is ordinary Python functions in one API process (`services/api/app/workflow/`). FastAPI is user-confirmed; the frontend stack was approved with the frontend plan (docs/design/FRONTEND_PLAN.md).

## Users

- **Primary: requesters.** Employees and business teams who describe a planned activity (for example sharing customer records with a new vendor) and need to know whether it complies with internal policy, what is missing, and what to do next.
- **Submission operator:** the student seeds the curated policy corpus through the CLI. Reviewer dispositions and upload/publishing administration remain future features; existing fixture screens do not establish live support.
- **Evaluation audience:** the capstone panel, who watch an 8-minute demo plus 2 minutes of Q&A and judge retrieval, the five-agent workflow, evidence traceability, evaluation and the UI.

## Product Purpose

Clause lets a person submit a natural-language compliance question or business scenario and receive the applicable policies, relevant clauses, citations, a structured compliance assessment, identified gaps or risks, and recommended actions. Success means every material finding can be traced to the exact clause, page and policy version that supports it, and what the system does not know stays visible.

## Positioning

Every verdict is pinned to its clause. Findings are structured records, not prose: each links to a validated citation in a pinned policy snapshot. Facts keep three states (provided, inferred, unknown), so an absent fact never becomes a negative assertion. Five specialist agents (retrieval, analysis, risk, validation, recommendation) hand off through an inspectable trace, and a validation step blocks conclusions that cited evidence does not support.

## Operating Context

- Planned submission workflow: describe the activity, answer one round of at most three clarifying questions (with an "I don't know" option), read the result and open its evidence. Reuse JSON export if time permits. Changed facts start a new assessment; a hypothetical branching engine is deferred.
- Result statuses: non_compliant, conflicting_policy, insufficient_information, compliant_within_scope, out_of_scope. Requirement statuses: met, violated, unknown, not_applicable, conflict.
- Policies have versions and effective dates; assessments pin an immutable snapshot.
- Planned live progress uses server-sent events from real workflow stages. Completed results are saved; an API restart interrupts active work and requires a new run. Exact-stage recovery is deferred.

## Capabilities and Constraints

- Corpus is the fictional Kestrel Mutual policy collection, confirmed by the user on 2026-09-26 for development, evaluation and the submission demonstration. It remains Kestrel unless the user explicitly requests a change. The UI must label it ("Demo corpus: fictional policies").
- Mock or fixture behavior must be visibly labeled and never presented as a live result.
- No compliance percentages, probability-of-compliance scores or invented confidence numbers.
- No invented evaluation metrics; only measured results from the evaluation harness may be shown.
- Deadline: 5 days from 2026-09-25.
- A reactive 3D avatar is a showcase feature; the app must work fully with it disabled.

## Brand Commitments

- Name: **Clause** (confirmed 2026-09-25).
- Visual direction chosen by the user: "Highlighter" (see docs/design/FRONTEND_PLAN.md). DESIGN.md is written after the build.

## Evidence on Hand

- IMPLEMENTATION_PLAN.md: authoritative reduced submission scope, core contracts in §5 and the vendor-sharing example in §10. Earlier task checklists and design briefs must be read against this revision.
- No real customers, testimonials, benchmarks or evaluation results exist yet; none may be fabricated.

## Product Principles

1. Evidence before prose: show the clause behind every conclusion.
2. Unknown stays unknown: never convert missing information into a verdict.
3. Honest status: label synthetic data, fixtures, hypotheticals and replays as such.
4. Explicit actions: run, cancel, resume, branch and export are always deliberate, visible controls.

## Accessibility & Inclusion

Full operation by keyboard and without the avatar, hover or animation; visible focus; status conveyed by text and icon, not color alone; WCAG AA contrast; reduced-motion support (IMPLEMENTATION_PLAN.md §12.5).
