# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + TypeScript + Vite frontend (`apps/web`), FastAPI + Pydantic backend (`services/api`), PostgreSQL + pgvector, LangGraph workflow, Docker Compose. FastAPI is user-confirmed; the frontend stack was proposed in IMPLEMENTATION_PLAN.md §4.1 and approved with the frontend plan (docs/design/FRONTEND_PLAN.md).

## Users

- **Primary: requesters.** Employees and business teams who describe a planned activity (for example sharing customer records with a new vendor) and need to know whether it complies with internal policy, what is missing, and what to do next.
- **Secondary: reviewers and admins.** Reviewers record dispositions on assessments; admins upload, version and publish policies.
- **Evaluation audience:** the capstone panel, who watch an 8-minute demo plus 2 minutes of Q&A and judge retrieval, the five-agent workflow, evidence traceability, evaluation and the UI.

## Product Purpose

Clause lets a person submit a natural-language compliance question or business scenario and receive the applicable policies, relevant clauses, citations, a structured compliance assessment, identified gaps or risks, and recommended actions. Success means every material finding can be traced to the exact clause, page and policy version that supports it, and what the system does not know stays visible.

## Positioning

Every verdict is pinned to its clause. Findings are structured records, not prose: each links to a validated citation in a pinned policy snapshot. Facts keep three states (provided, inferred, unknown), so an absent fact never becomes a negative assertion. Five specialist agents (retrieval, analysis, risk, validation, recommendation) hand off through an inspectable trace, and a validation step blocks conclusions that cited evidence does not support.

## Operating Context

- Case workflow: describe the activity, answer at most three prioritized clarifying questions (with an "I don't know" option), read the verdict, open the evidence, optionally branch a hypothetical, export a report.
- Result statuses: non_compliant, conflicting_policy, insufficient_information, compliant_within_scope, out_of_scope. Requirement statuses: met, violated, unknown, not_applicable, conflict.
- Policies have versions and effective dates; assessments pin an immutable snapshot.
- Live progress arrives as server-sent events from real workflow stages.

## Capabilities and Constraints

- Corpus is a synthetic, fictional organization's policies until the assessor supplies real documents; the UI must label it ("Demo corpus: fictional policies").
- Mock or fixture behavior must be visibly labeled and never presented as a live result.
- No compliance percentages, probability-of-compliance scores or invented confidence numbers.
- No invented evaluation metrics; only measured results from the evaluation harness may be shown.
- Deadline: 5 days from 2026-09-25.
- A reactive 3D avatar is a showcase feature; the app must work fully with it disabled.

## Brand Commitments

- Name: **Clause** (confirmed 2026-09-25).
- Visual direction chosen by the user: "Highlighter" (see docs/design/FRONTEND_PLAN.md). DESIGN.md is written after the build.

## Evidence on Hand

- IMPLEMENTATION_PLAN.md: domain model, API contracts, the §5.3 assessment fixture and the §10 vendor-sharing worked scenario.
- No real customers, testimonials, benchmarks or evaluation results exist yet; none may be fabricated.

## Product Principles

1. Evidence before prose: show the clause behind every conclusion.
2. Unknown stays unknown: never convert missing information into a verdict.
3. Honest status: label synthetic data, fixtures, hypotheticals and replays as such.
4. Explicit actions: run, cancel, resume, branch and export are always deliberate, visible controls.

## Accessibility & Inclusion

Full operation by keyboard and without the avatar, hover or animation; visible focus; status conveyed by text and icon, not color alone; WCAG AA contrast; reduced-motion support (IMPLEMENTATION_PLAN.md §12.5).
