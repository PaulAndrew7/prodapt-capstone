# Model-independent operation — 30 September 2026

Implemented the [fallback plan](../OFFLINE_FALLBACK_IMPLEMENTATION_PLAN.md) after planning the execution policy, confirmation semantics, failure boundaries, persistence and acceptance checks. The change extends the existing app and coverage gate.

## Delivered behavior

- `LLM_MODE=auto` defaults to local review when provider settings are absent/incomplete and switches after a model error. `offline` skips provider-client construction even with credentials; `required` preserves strict errors for diagnostics/model-only operation. Default stage-call timeout: 20 seconds, including gateway continuations and bounded by the run deadline.
- Model SDK errors, authentication/rate/transport failures, refusal/truncation, malformed success envelopes, invalid stage JSON and budget/deadline errors follow the model failure boundary. Unrelated database/programming errors are not masked. Provider bodies are excluded from local reports and events.
- Failure in analysis, validation or recommendation discards model findings/facts, reuses the retrieved evidence and switches once. Execution metadata persists through clarification. Removing the provider while a saved run waits also switches it locally. A fresh run may try the provider again.
- Local review uses the same organization, snapshot, date and retrieved-candidate selection. Each candidate gets a source-linked unknown finding until an explicit enumerated disposition is recorded. User confirmations retain message provenance across batches of three. Unknown answers are not repeatedly asked; stale/invalid submissions are rejected.
- Early finish saves remaining checks as unknown. A reported breach can decide non-compliance; unknowns block clearance. All-satisfied/all-excluded results explicitly depend on user confirmations, remain scoped to retrieved evidence and stay unreviewed. Empty local retrieval does not grant clearance.
- Source/choice checks, risk, final-status/coverage rules and template recommendations run without a model. Local results omit numerical evidence scores. Lookup returns exact ranked excerpts with source/version/PDF links.
- Execution mode, trigger, local version and bounded failed stage/code are saved in assessment/run JSON. SSE announces fallback and resets progress after retrieval. UI notices, trace handoffs and print/export provenance distinguish local review from model interpretation. Historical results remain readable. No migration or new service is needed.

## Verification

Full backend suite, including PostgreSQL integration: **272 passed**, with no skips. Frontend unit suite: **43 passed**. Full browser suite: **26 passed**, covering desktop/mobile, keyboard early completion, print, existing flows, source links and accessibility. Current frontend production build passed with the existing large-bundle advisory. TypeScript, backend Ruff/mypy (43 source files) and OpenAPI freshness passed.

Two real transport checks used a temporary API with `LLM_MODE=offline`, `EMBEDDINGS_ENABLED=false` and the separate evaluation database. The client factory returned `None`; no LLM request was made:

1. HTTP: cited lookup returned four exact excerpts. A nine-candidate assessment retained three confirmations across batches, completed with remaining checks unknown, preserved the saved result, and exposed its original PDF redirect and SSE metadata.
2. Browser → API: created a fresh case, recorded one user-reported breach plus unknowns, submitted a batch, finished subsequent checks as unknown, and saved non-compliance attributed to that confirmation. Nine candidates were accounted for; there were zero browser errors. This used the actual API rather than the UI fixture.

Mobile fixture and actual desktop result screenshots were visually inspected; the local controls wrap without horizontal overflow. Temporary artifacts are in `tmp/offline-smoke/` and `tmp/local-review-*.png`; fixture screenshots are explicitly labelled. The temporary API/Vite helpers used 8001/5175 and were closed. The user's `.env`, configured credentials and normal demo database were not changed.

The backend tests use local provider stubs and a separate PostgreSQL test database. SDK platform-header construction emitted Windows WMI allocation diagnostics in two runs; both test processes continued, completed all checks and exited zero. Existing Alembic deprecation and frontend bundle advisories remain.

## Limits and evaluation

This is a model-independent evidence review, requiring human interpretation. It does not infer facts from free-form narrative, independently establish applicability, resolve semantic policy conflicts or prove full-policy retrieval coverage. “Validated” in local mode describes source and recorded-disposition checks in code. Typed user answers are attributed rather than treated as independently verified claims.

No evaluation answer keys were encoded in the fallback. Existing model development reports remain unchanged, and no held-out or paid model benchmark was run in this batch. Availability tests do not establish model-quality accuracy. Downloaded local LLMs, reviewed policy-rule compilation and durable workers remain future work.
