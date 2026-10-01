# Model-independent operation and failure fallback

Prepared 30 September 2026. This plan extends the working assessment, source lookup and coverage inspector. It is implemented in the same application and database; it requires no local language-model download or additional service.

## Intended behavior

The app should continue to retrieve policies, display sources, complete assessments and export results when a language model is absent or a model request fails. A fallback result must explain how it was produced. An outage must not turn an unchecked scenario into a compliant result.

The local path is an **evidence review workflow**. It retrieves the dated policy bundle, creates one check per requirement candidate and asks the requester to explicitly confirm applicability and satisfaction. Code checks the recorded choices, source references, coverage and final-status rules. It does not claim to understand arbitrary narrative text or independently validate a user's interpretation. Unconfirmed dispositions remain unknown. This makes it useful across the existing corpus without encoding evaluation answers or trying to approximate a language model with fragile keyword rules.

Policy questions have a different local path: return ranked, exact excerpts with their clause, version and original PDF page. The response identifies itself as source excerpts requiring interpretation. It never fabricates a synthesized answer.

## Configuration and selection

`LLM_MODE` has three policies:

| Mode | Behavior |
|---|---|
| `auto` (default) | Use a fully configured model; use local review if absent or incomplete; switch after a model error |
| `offline` | Skip model-client construction and all model calls, even when credentials exist |
| `required` | Preserve strict configuration and fail on model errors; useful for diagnosing the provider and measuring model-only behavior |

`LLM_CALL_TIMEOUT_SECONDS` caps each budgeted model call, including continuations, before automatic fallback. Default: 20 seconds, also bounded by the existing run deadline. A schema repair is a second budgeted call with the same cap; existing repair and call-count limits remain. Missing credentials/model/base URL may select local review in automatic mode; malformed URLs and unsafe application configuration still fail validation.

The local path still requires the seeded policy corpus, original source storage and PostgreSQL. Local embeddings remain optional. `EMBEDDINGS_ENABLED=false` provides lexical-only operation without an embedding download. No model failure handler catches database, source-ingestion or application-programming errors.

## Assessment execution

1. Retrieve evidence with the same organization, snapshot and assessment-date restrictions as today.
2. Select the model path or local path. Persist execution metadata on the run, including mode, trigger, local-engine version and the failed model stage/code when relevant. Persist only a bounded error code, not provider response bodies or secrets.
3. If any analysis, validation or recommendation model call fails, switch once to local review using the same retrieved bundle. Discard that attempt's model-derived findings and facts. Keep the earlier stage events as audit history and append a fallback event that resets progress for the local path.
4. Pin the local choice to the run. Clarification resumes must not call a failed provider again. A fresh run may try the configured provider again.
5. Produce a finding for every retrieved candidate using the coverage gate's classifications/catalog. Quote actual stored text. Before a confirmation, the disposition is unknown and the reason explicitly says local review has not established applicability or satisfaction.
6. Ask at most three source-linked questions at a time. Choices: applies and satisfied, applies and breached, or does not apply; the existing “I don't know” action preserves unknown. Only these exact choices may decide a finding. Arbitrary text, instructions in the scenario and unsolicited answer keys cannot grant clearance.
7. Save answers cumulatively across local batches with their message provenance. Do not re-ask a check answered as unknown. Distinct question IDs and the existing run lock protect against stale/duplicate submissions. The dated bundle bounds the number of questions.
8. Let the user finish early with remaining checks unknown. This produces a useful completed report instead of forcing a long checklist during an outage. It cannot grant clearance when checks remain unknown.
9. Verify references and quote matching in code. Generate recommendations from fixed templates tied to unknown or user-reported breached clauses. Retain the risk rubric and coverage gate. No model stage runs on this path.
10. Compute the final status from recorded dispositions. A user-confirmed breach remains decisive; unknowns prevent compliance. A local clearance or out-of-scope result explicitly attributes applicability/satisfaction to the user's confirmations and remains unreviewed. Empty retrieval produces insufficient information rather than claiming the entire corpus is irrelevant.

Local findings do not borrow a model-derived numerical evidence score. Execution notices and limitations explain that source checks and typed confirmations replaced semantic validation. Reports show the engine and trigger, so a local assessment cannot be mistaken for a model assessment.

## Lookup execution

Search first. With a configured model, preserve the existing grounded-answer path. If there is no model or a request fails, build citations directly from the first few ranked source clauses and display exact excerpts. Retain organization/date/policy filters and original page links. An empty result says search found no evidence; it does not assert no policy exists. Failed model text is never returned as a fallback answer.

## Contracts, UI and persistence

- Add optional execution metadata to assessments, lookup answers, case details and run responses. Historical records remain readable; metadata is not fabricated for old results.
- Add a fallback SSE event and mirror it in the browser subscription/store. Preserve replay, deduplication, cancellation and terminal-state behavior.
- Show a local-review notice during clarification and with the final assessment. Show source-excerpt mode above local lookup results. Include the engine/trigger in print and JSON exports.
- Add a “Finish with remaining checks unknown” control only for local review. Each question links to the actual clause. New batches have independent form state.
- Save metadata in existing JSON columns, requiring no database migration.

## Implementation sequence

1. Contracts/configuration/client selection and bounded call timeout.
2. Deterministic local analysis, reference validation, recommendations, summaries and extractive lookup.
3. Orchestrator failover, sticky execution metadata, cumulative clarification and early completion.
4. API and browser notices, progress reset, local clarification actions, print/export metadata.
5. Fault-injection and no-model verification; documentation and demo instructions.

## Acceptance checks

| Scenario | Required evidence |
|---|---|
| No provider / missing credentials | Application starts; lookup returns cited excerpts; assessment can finish locally |
| Forced offline with configured credentials | A spy model receives zero calls |
| Authentication, rate limit, transport, timeout, truncated/invalid output, call-budget exhaustion | One automatic switch; visible bounded reason; no failed-model claims survive |
| Failure in analysis, validation or recommendation | Same dated evidence reused; local result/clarification succeeds |
| Clarification after failure | Provider stays unused; earlier confirmations are retained |
| Provider removed while waiting | Saved model run switches to local mode; prior model answers cannot decide local findings |
| Unknown and partial confirmations | No invented breach or compliance; early finish produces a saved report |
| All checked / one reported breach / all excluded | Deterministic outcomes reflect explicit confirmations and remain unreviewed |
| Invalid/stale answer, duplicate request, cancellation | Rejected or deduplicated without corrupting run state; canceled run never publishes |
| Version boundary and foreign organization | Existing source/date/organization restrictions still apply |
| Lookup and no retrieval hits | Exact source excerpts or explicit absence of retrieved evidence; no fabricated synthesis |
| Web desktop/mobile, keyboard, print/export | Mode visible, source links work, question batches reset, report includes provenance |
| Regression suite | Backend/database, contracts/OpenAPI, types, unit/browser tests and production build pass |

No paid real-model benchmark is needed to prove failover. Scripted faults exercise model boundaries, while a temporary API with `LLM_MODE=offline` and lexical-only retrieval proves operation with no external model calls. Existing model development reports remain unchanged. Held-out labels are not used to construct this feature.

## Presentation story and remaining scope

Show the same policy source and assessment date in model and local modes. Explain the failed stage, the local confirmation, the saved source trace and why unknowns prevent clearance. Distinguish availability from interpretation quality: the application remains useful during an outage, while human interpretation is explicit.

A downloaded local language model, automatic policy-to-rule compilation and a durable worker are later enhancements. They require separate model/hardware evaluation or reviewed rule semantics. This batch provides a dependable model-independent baseline first.

## Implementation delivered

All five implementation steps are complete. The backend local engine is in `services/api/app/workflow/local_review.py`; orchestration, provider-envelope validation and bounded calls use the existing workflow. API and browser contracts now carry execution metadata. Local notices, repeated confirmation batches, early finish, SSE progress resets, print and JSON exports are implemented without a schema migration.

The README documents all three execution policies and a fully local setup; the presentation runbook includes an outage/local demonstration. Verification details and remaining semantic limits are recorded in [the implementation session record](tasks/SESSION_2026-09-30_OFFLINE.md). No LLM provider call or paid model benchmark was used to build or verify this fallback.
