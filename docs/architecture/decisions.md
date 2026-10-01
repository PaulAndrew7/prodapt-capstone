# Decisions and tradeoffs, as built

This page describes the submitted implementation (26 September 2026). The numbered ADRs in this folder record earlier, larger plans; where they differ, this page and the [implementation plan](../../IMPLEMENTATION_PLAN.md) describe what the code does. Diagram: [architecture.pdf](architecture.pdf) ([system](architecture-system.jpg), [workflow](architecture-workflow.jpg)); editable source in [diagram/architecture.html](diagram/architecture.html).

Each entry gives the choice, the main alternative, what it costs, and the evidence that would change it.

## Model-independent fallback (30 September 2026)

`LLM_MODE=auto` uses a configured provider and switches to a local evidence review on `ModelError`. Absent or incomplete model settings start locally. `offline` constructs no provider client; `required` retains strict failure behavior. A stage call, including continuations, is capped by `LLM_CALL_TIMEOUT_SECONDS` (20 seconds by default) and the remaining run deadline. SDK transport/status errors, malformed provider envelopes and invalid stage JSON are mapped to model errors. Database and programming errors are still failures.

Local review retrieves the same organization/date/snapshot-pinned bundle, creates an unknown check for each requirement candidate, and collects enumerated, source-linked user dispositions in batches of three. Confirmations persist across batches; users can finish early with remaining checks unknown. Code verifies source quotes and recorded choices, uses template actions and the existing risk/status/coverage rules. It does not semantically interpret narrative text, resolve policy conflicts or independently verify the user's applicability decisions. Results remain unreviewed and have no numerical evidence score. No retrieval candidates means insufficient information.

Failure switches once using the evidence already retrieved and discards model-derived facts/findings. The run persists the local choice through resumes; a new run may retry the provider. Bounded trigger/stage/error metadata is saved in existing JSON columns, emitted through SSE and handoffs, and included in the UI and reports. Lookup falls back to exact source excerpts, never failed-model text or invented synthesis. No migration, downloaded LLM or extra service is needed. Embeddings can be disabled for lexical-only operation.

This trades automated interpretation for an explicit human review process, while retaining useful source access and durable results during an outage. Policy-to-rule compilation or a local model would need separate semantic/hardware evaluation. See [the design and acceptance plan](../OFFLINE_FALLBACK_IMPLEMENTATION_PLAN.md).

## Evidence coverage gate (30 September 2026)

The final result now accounts for retrieved requirement candidates independently of the model's findings. Requirement and exception clauses are candidates; a reviewed policy-derived catalog includes general clauses that express obligations without modal verbs. Definition clauses remain context. Every candidate needs a validated assessment or a validated not-applicable disposition. Merely citing a clause does not account for its requirement.

Unresolved candidates produce insufficient information rather than compliant or out of scope; established breaches and conflicts retain precedence. This deliberately favors review over silently clearing an incomplete assessment, including when analysis claims nothing applies without justifying exclusions. It can cause more abstention on irrelevant search hits. The saved coverage rows expose this tradeoff and distinguish omissions from unsupported findings. It cannot detect retrieval misses or prevent a validator from accepting an incorrect interpretation. Evaluation reports now measure both unjustified clearance and cautious misses; the 29 September raw reports predate the gate.

Coverage is stored in assessment JSON and the validation handoff. No schema migration or extra model stage is needed. Older assessments remain unchanged and display “coverage not recorded.” Finding evidence scores remain; a headline withheld for unresolved coverage has an incomplete-check score of zero with an explicit basis, rather than borrowing a met finding's score or implying that no requirement applies.

The analysis-v3 prompt receives a candidate checklist derived from the same evidence and policy metadata. It must assess or explicitly exclude every candidate. A no-applicable-policy flag no longer discards proposed exclusions before validation. On the configured Claude Sonnet 5.5, adding the gate alone left unresolved candidates in all 13 development runs; adding the checklist reduced that to one run with one disputed exclusion. The latest result is 12/13 final statuses correct, with one cautious miss. This is a development observation, not a held-out estimate or a comparison holding the provider fixed against the older GPT-4o mini baseline. See [evaluation analysis](../evaluation/analysis.md).

## Shape of the system

**One FastAPI process runs the API and the assessment.** A run starts as an in-process background task, so `POST /cases/{id}/runs` returns a run ID immediately and the browser follows progress over SSE.
- Instead of: a separate worker with a job queue and leases (ADR 001's original plan).
- Cost: restarting the API interrupts an active run. On startup, queued and running runs are marked failed with a clear message; completed results and runs waiting for answers are kept. There is no recovery from the exact interrupted stage.
- Revisit if: several people must run assessments at once, or runs must survive restarts.

**Five roles are ordinary Python functions in a fixed order** (`app/workflow/orchestrator.py`): retrieval, compliance analysis, risk, validation, recommendation, then final checks.
- Instead of: a graph framework such as LangGraph, or agents negotiating until they agree.
- Cost: no general dynamic routing. The model path has one clarification round; the local path repeats bounded confirmation batches over the retrieved bundle.
- Revisit if: a measured case category needs a different path through the stages.

**Only three steps call the model when one is available.** Retrieval and risk are deterministic code; model-mode validation is code plus one model check. A normal model run uses three calls, under a limit of 8 calls and 120 seconds per attempt, with at most one schema repair per stage. Local review uses zero model calls and checks sources and recorded dispositions in code.
- Instead of: a model call per role, or open-ended tool use.
- Cost: the risk rubric is simple (`demo-risk-v1`: high for a supported breach about customer data or access, medium for other mandatory breaches, no severity for unknowns). It does not estimate likelihood.
- Revisit if: evaluation shows severity labels that reviewers disagree with.

**Handoffs are typed application messages, not the Agent2Agent protocol.** Each stage saves a progress event and a handoff record (sender, receiver, message type, summary, payload), which the trace view shows.
- Revisit if: the assessor requires the standardized protocol (plan F28).

**PostgreSQL comes from a Python package, not Docker.** `python -m app.cli db-start` (`app/localdb.py`) runs PostgreSQL 16 with pgvector from the `pixeltable-pgserver` wheel that `uv sync` installs, on port 5433 with its data in `var/postgres`. CI starts the database the same way.
- Instead of: Docker Compose (used until 29 September 2026), or a native PostgreSQL install, which on Windows means building pgvector by hand.
- Cost: the database version is whatever the pinned wheel ships (0.5.1: PostgreSQL 16, pgvector 0.8.1; the 0.6.0 Windows build of pgvector crashes on CPUs without AVX-512). The server is a background process rather than a service, so it has to be started again after the computer restarts.
- Evidence: the backend tests pass against it on Windows and Linux, and the 13 development scenarios return the same top-10 search results as on the earlier Docker database.
- Revisit if: the app moves to a shared server, where a managed PostgreSQL fits better.

## Retrieval and evidence

**Search runs inside PostgreSQL.** Full-text ranking and pgvector similarity are fused by reciprocal rank fusion; the score is an ordering, not a confidence.
- Instead of: a separate vector database or a reranker.
- Evidence: on the 13 development scenarios, hybrid Recall@10 is 0.839 against 0.704 for keyword search alone ([results-dev.md](../evaluation/results-dev.md)).
- Cost: one fixed embedding model and no reranking. Purpose-limitation clauses are rarely retrieved ([analysis.md](../evaluation/analysis.md)).
- Revisit if: an assessment failure is traced to a missing clause that a reranker or a reviewed clause link would fix.

**Embeddings are computed locally** (BAAI/bge-small-en-v1.5 through fastembed). Search and ingestion need no API key and send no policy text off the machine.

**The evidence bundle is the top 10 search hits plus the clauses needed to read them** (cited clauses, exceptions, definitions), capped at 14. Ten was chosen on development data only: it raised bundle recall from 0.822 (eight hits) to 0.856.

**The model picks clause IDs and quotes; the server builds every citation.** Validation rejects a reference to a clause outside the run's retrieved evidence and a quote that does not appear in the clause. Citation text, version and page come from stored records.
- Cost: a matching quote proves the text exists, not that the interpretation is right. The model support check and human evaluation cover interpretation.

**Policy versions come from a saved snapshot and the activity date.** Drafts are excluded, and a clarification rerun keeps the original snapshot.

## Results

**The overall result comes from five ordered rules in Python** (`app/workflow/outcome.py`): a validated violation gives `non_compliant`, then conflict, then unknowns or unconfirmed claims give `insufficient_information`, then validated `met` gives `compliant_within_scope`, otherwise `out_of_scope`.
- Instead of: asking the model for an overall verdict or a compliance percentage.
- Why: an unconfirmed claim can never produce a compliant result, and "approval was not mentioned" (unknown) stays distinct from "we have not obtained approval" (violated).

**Model-assisted verdicts carry a confidence score computed in code** (`app/workflow/confidence.py`): each finding, the overall result and each lookup answer get a 0-100 evidence score with a high/medium/low band and the factors behind it. A finding scores validation (40), an exact quote (20), stated rather than inferred facts (25) and search rank (15). The result takes the deciding finding's score: the strongest breach, or the weakest met requirement for a compliant result. Local review omits this metric because it has no independent semantic validation.
- Instead of: asking the model to rate itself (poorly calibrated) or rerunning it several times and measuring agreement (about three times the cost and time).
- Why: every point traces to a check the run recorded, so it is explainable and testable without a model. It ranks how well a verdict is backed; it is not a probability, and it is not a compliance percentage. `evaluate` reports accuracy per band, which is the measured link between score and correctness.

**The final assessment is one JSON document on the run.** It is validated by the Pydantic contract in `app/domain/contracts.py`, which the TypeScript types in `apps/web/src/lib/api/types.ts` mirror field for field (`packages/contracts/openapi.json` is exported from the same models). The normalized finding and risk tables in the schema are unused.
- Revisit if: a feature needs to query findings across cases.

**Model clarification is one round of at most three questions**, with "I don't know" allowed. Resuming reruns the stages with the answers and does not pause again, so unanswered facts stay unknown. Local review permits multiple batches, retains all answers and allows early completion with unknowns.

## Model access

**Claude Sonnet 5.5 through the Anthropic API** (the owner's own key, 30 September 2026). `LLM_PROVIDER=anthropic` selects `app/workflow/claude_model.py`, which implements the same `ModelClient` interface as the gateway client, so the stages and prompts are unchanged.
- Structured outputs (`output_config.format`) constrain each reply to the stage's JSON Schema; the reply is still validated against the stage's Pydantic model with one repair request at most. There is no 500-token cap, so no continuations.
- `LLM_EFFORT=low` sets Sonnet 5.5's thinking effort; thinking counts against the 16,000-token `max_tokens`. Claude Haiku 4.5 rejects the effort setting, so it is left unset there.
- Evidence: the latest development runs (30 September) used it; the analysis-v3 run took about 10,000 input and 3,000 output tokens per assessment, median 21.4 s.
- Also supported: Claude Haiku 4.5 (`LLM_MODEL=claude-haiku-4-5`), cheaper for test runs, whose results are not comparable with the Sonnet numbers; and the organizers' gateway below, which the project ran on first.
- Cost: per-token billing on a personal key, and slower runs than the gateway (21.4 s against 8.4 s median), because the checklist output is larger and the model thinks first.

**GPT-4o mini through the organizers' gateway** (`https://keygateway1.arshnivlabs.com/v1`, lab key, 29 September 2026). `LLM_PROVIDER=openai_compatible` selects `app/workflow/llm.py`: the official OpenAI SDK pointed at `LLM_BASE_URL`. The gateway is OpenAI-shaped but narrower than the OpenAI API, and three settings follow from its published request schema:
- No model name is sent (`LLM_MODEL` unset). The gateway always serves `gpt-4o-mini`, and its instructions say not to set one.
- `LLM_JSON_MODE=json`: it accepts `response_format` only as the string `"json"` or `"text"`, so there is no schema-constrained output. The stage's JSON Schema goes in the system message, and the reply is validated against the stage's Pydantic model with one repair request at most, as for every provider.
- `LLM_MAX_OUTPUT_TOKENS=500`: it rejects anything higher. An analysis reply can need about 1,000 tokens, so a reply that stops at the cap (`finish_reason: length`) is continued. The client trims the partial reply to its last complete line (GPT-4o mini restarts a cut-off line, and a mid-line seam produced broken JSON), sends it back as the assistant turn, asks for the rest as plain text, drops any repeated text when joining, and stops after three continuations. The budget still counts one call per stage and records the extra HTTP requests as `model_requests`. In the final development run, 7 of 13 assessments needed a continuation (39 requests for 32 stage calls), and none failed.
- `LLM_TEMPERATURE=0`: the gateway's default is 1.0. Zero did not make runs identical, but a compliance check should not vary by design.
- Instead of: splitting the analysis stage into several smaller calls. That would change the prompts and how findings are merged, while continuation is contained in the client and leaves the stages unchanged.
- The Claude client above was first added on 29 September while the organizers' key was missing. One provider is configured at a time; automatic fallback uses local review rather than a second provider.
- Cost: no schema-constrained output, and continuation requests add latency (median run 8.4 s on the development set).
- Security: the key is read by the API only, never sent to the browser or logged.

## Data and evaluation

**The corpus is fictional** (Kestrel Mutual: 11 policies, 14 versions, 111 clauses), authored as Markdown and rendered to digital PDFs. See [corpus-decision.md](../data/corpus-decision.md). OCR and DOCX are out of scope.

**Evaluation uses the same workflow on labelled scenarios in a separate database** (`python -m app.cli evaluate`). There are 13 development scenarios for tuning and 20 held-out scenarios that are reviewed, frozen and then run once. The sample is small; results describe this corpus, not general accuracy.

## Operation

**Local demonstration only.** `AUTH_MODE=demo` maps every request to the seeded demo user, and production settings refuse it. Public hosting needs real authentication first.

**The frontend is the existing React app.** Live mode connects Policies, Ask a question and Cases to the API. Screens without a backend (review, reports, evaluation lab, settings) are labelled as prototypes.
