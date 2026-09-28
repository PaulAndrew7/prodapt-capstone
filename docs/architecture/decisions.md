# Decisions and tradeoffs, as built

This page describes the submitted implementation (26 September 2026). The numbered ADRs in this folder record earlier, larger plans; where they differ, this page and the [implementation plan](../../IMPLEMENTATION_PLAN.md) describe what the code does. Diagram: [architecture.pdf](architecture.pdf) ([system](architecture-system.jpg), [workflow](architecture-workflow.jpg)); editable source in [diagram/architecture.html](diagram/architecture.html).

Each entry gives the choice, the main alternative, what it costs, and the evidence that would change it.

## Shape of the system

**One FastAPI process runs the API and the assessment.** A run starts as an in-process background task, so `POST /cases/{id}/runs` returns a run ID immediately and the browser follows progress over SSE.
- Instead of: a separate worker with a job queue and leases (ADR 001's original plan).
- Cost: restarting the API interrupts an active run. On startup, queued and running runs are marked failed with a clear message; completed results and runs waiting for answers are kept. There is no recovery from the exact interrupted stage.
- Revisit if: several people must run assessments at once, or runs must survive restarts.

**Five roles are ordinary Python functions in a fixed order** (`app/workflow/orchestrator.py`): retrieval, compliance analysis, risk, validation, recommendation, then final checks.
- Instead of: a graph framework such as LangGraph, or agents negotiating until they agree.
- Cost: no dynamic routing. One clarification round and a fixed sequence cover the demonstrated cases.
- Revisit if: a measured case category needs a different path through the stages.

**Only three steps call the model.** Retrieval and risk are deterministic code; validation is code plus one model check. A normal run uses three model calls, under a limit of 8 calls and 120 seconds per attempt, with at most one schema repair per stage.
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

**The final assessment is one JSON document on the run.** It is validated by the Pydantic contract in `app/domain/contracts.py`, which the TypeScript types in `apps/web/src/lib/api/types.ts` mirror field for field (`packages/contracts/openapi.json` is exported from the same models). The normalized finding and risk tables in the schema are unused.
- Revisit if: a feature needs to query findings across cases.

**Clarification is one round of at most three questions**, with "I don't know" allowed. Resuming reruns the stages with the answers and does not pause again, so unanswered facts stay unknown.

## Model access

**GPT-4o mini through the organizers' gateway, using their key** (plan §4.4). `app/workflow/llm.py` has one client: the official OpenAI SDK pointed at `LLM_BASE_URL`. It asks for strict JSON-schema output, falls back to JSON-object mode if the gateway lacks schema support (`LLM_JSON_MODE`), and can send the key in a named header (`LLM_API_KEY_HEADER`). Every reply is validated against the stage's Pydantic model either way.
- Instead of: a provider-routing layer or automatic fallback to another service.
- Cost: nothing model-backed runs until the key arrives. The client is tested against a local stub server only; `python -m app.cli check-model` is the first live check.
- Security: the key is read by the API only, never sent to the browser or logged.

## Data and evaluation

**The corpus is fictional** (Kestrel Mutual: 11 policies, 14 versions, 111 clauses), authored as Markdown and rendered to digital PDFs. See [corpus-decision.md](../data/corpus-decision.md). OCR and DOCX are out of scope.

**Evaluation uses the same workflow on labelled scenarios in a separate database** (`python -m app.cli evaluate`). There are 13 development scenarios for tuning and 20 held-out scenarios that are reviewed, frozen and then run once. The sample is small; results describe this corpus, not general accuracy.

## Operation

**Local demonstration only.** `AUTH_MODE=demo` maps every request to the seeded demo user, and production settings refuse it. Public hosting needs real authentication first.

**The frontend is the existing React app.** Live mode connects Policies, Ask a question and Cases to the API. Screens without a backend (review, reports, evaluation lab, settings) are labelled as prototypes.
