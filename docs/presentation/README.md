# Presentation: script, demo runbook and question prep

Ten minutes: eight minutes of walkthrough, two for questions (plan §17). Everything shown must be real output. Where this page says **[fill in]**, use the measured value from `docs/evaluation/`. Never use a target or an example number instead.

Visuals: [architecture-system.jpg](../architecture/architecture-system.jpg), [architecture-workflow.jpg](../architecture/architecture-workflow.jpg) (or [architecture.pdf](../architecture/architecture.pdf)), and the running app.

## Before the session (allow 20 minutes)

1. Start Docker Desktop, then `docker compose up -d db`.
2. `cd services/api`, then `uv run python -m app.cli migrate` and `uv run python -m app.cli seed-demo`.
3. Put the organizers' gateway settings in `.env` and run `uv run python -m app.cli check-model`. It must print `OK`; note the served model and response time.
4. Start the API with `uv run uvicorn app.main:app --port 8000`. In a second terminal, from the repo root, run `VITE_API_MODE=http corepack pnpm --dir apps/web dev`.
5. **Saved fallback:** run the demo scenario once end to end, and keep that completed case. If the live run is slow or the gateway fails during the talk, open this case instead and say so.
6. **Recorded fallback:** screen-record that rehearsal run (about 90 seconds) and label it "recorded on <date>".
7. Open these tabs:
   - `http://localhost:5173/app/policies`
   - `http://localhost:5173/app/cases/new`
   - the saved case
   - the two architecture JPEGs
   - `docs/evaluation/results-test.md`
8. Close notifications, set browser zoom to 110–125%, and keep `.env` out of view.

## Walkthrough

| Time | Show | Say (in your own words) |
|---|---|---|
| 0:00–1:00 | Front page, then Policies | "Staff must check plans against a stack of internal policies. Clause checks a described activity against them and shows exactly which clause each finding rests on. The policies belong to Kestrel Mutual, a fictional insurer I wrote: 11 policies, 14 versions and 111 clauses. None of it is real policy or legal advice." |
| 1:00–2:00 | Policies → Customer Data Sharing Policy v1 → §4.2 → open the source page | "Each PDF is parsed into numbered clauses with page positions. Versions have effective dates. v2 of this policy starts on 1 October, so the date of an activity decides which text applies." |
| 2:00–4:00 | New case → **Share data with a new vendor** sample (or paste the §10 scenario) → date 26 September 2026 → **Assess**. Watch the stages; answer the vendor question with "I don't know". | "The stages you see finish in real time. Retrieval found the clauses, and analysis noticed a missing fact, so it asks me rather than guessing. 'I don't know' is allowed; that fact then stays unknown." |
| 4:00–5:00 | Result: the **non-compliant** headline, then the Data Sharing §4.2 finding → evidence drawer → source page | "Data-owner approval is *violated* because I said it wasn't given. Vendor review is *unknown*, not violated, because nobody said it failed. The quote is checked against the stored clause, and the page link opens the original PDF." |
| 5:00–6:00 | Workflow diagram, then the **Trace** tab | "Five roles, each an ordinary Python function with its own output schema. Retrieval and risk are code; analysis, the validation check and recommendation are one model call each. Each arrow is a saved handoff you can inspect here. Final rules decide the status, so an unconfirmed claim can never make a result compliant." |
| 6:00–7:00 | `results-test.md` and one failure from `analysis.md` | "On 20 held-out scenarios, frozen before the run: status accuracy **[fill in]**, false-compliant **[fill in] of [fill in]**, citation validity **[fill in]**, median run time **[fill in]**. Hybrid search found **[fill in]** of labelled clauses in the top ten. One failure: **[fill in: a real one from analysis.md]**." |
| 7:00–8:00 | System diagram | "One FastAPI process, one Postgres database with vector search, and local embeddings. The only external call is to GPT-4o mini through the organizers' gateway, and the key never reaches the browser. Limits: a small fictional evaluation, one user, and a restart fails a running assessment. Setup is five commands in the README." |
| 8:00–10:00 | Questions | See below. |

**Changed-facts demo (only if there is time):** on the completed case, send "The data owner has now approved it in writing and it is in the register" from the conversation box. A follow-up starts a new run, and the earlier result stays in history. §4.2 can become *met*, but vendor review is still unknown, so the result does not become compliant. One changed fact does not settle the whole case.

**If the live run fails:** say what happened ("the gateway timed out; a failed run is recorded as failed, never as a result"), then open the saved case. This also demonstrates the failure handling.

## Questions to prepare

Each answer should point at code you can open.

| Question | Short answer | Where to show it |
|---|---|---|
| Why five agents? | The brief asks for five roles. Each is one function with one responsibility and a typed output passed to the next. They share one backend and one model configuration; they are not autonomous agents negotiating. | `services/api/app/workflow/orchestrator.py` (`_stages`) |
| How do you access the model? | FastAPI sends HTTPS requests through the organizers' gateway to GPT-4o mini, with their key stored server-side. One client, strict JSON schema, every reply validated, one repair at most. | `app/workflow/llm.py`; `check-model` |
| What is RAG here? | Search the policy text first, then give only those clauses to the model and make it cite them. | `app/workflow/retrieval.py` |
| Why keyword and vector search? | Keywords match policy terms; vectors match different wording. Combining the rankings measured 0.839 Recall@10 against 0.704 for keywords alone on dev data. | `app/retrieval/search.py`; `results-dev.md` |
| How do citations work? | The model names clause IDs and quotes. The code rejects IDs outside the retrieved evidence and quotes not in the clause, then builds the citation (text, version, page) from the database. | `app/workflow/validation.py` (`check_references`) |
| Does validation guarantee correctness? | No. It proves the quote exists; whether it supports the conclusion is a model check plus evaluation, and some interpretations will still be wrong. | `analysis.md` failures |
| What if facts are missing? | Up to three questions, one round. Unanswered facts stay unknown, and unknown leads to "insufficient information", never "compliant". | `app/workflow/outcome.py` |
| Why no LangGraph or agent framework? | The flow is fixed with one pause; plain functions are easier to test and explain. | `orchestrator.py` |
| Why one database and one API? | The demo fits one machine; Postgres does both records and vector search. | `compose.yaml`; system diagram |
| What happens after a restart? | Completed results stay saved. A run in progress is marked failed ("interrupted") on startup and must be started again. | `fail_interrupted_runs` in `orchestrator.py` |
| How do you know it works? | Automated tests with a scripted model, a fresh-setup check, and the held-out evaluation with its failures. The sample is small. | `services/api/tests/`; `docs/evaluation/` |
| Did you train a model? | No. The work is the corpus, ingestion, retrieval, workflow, validation, evaluation and the app around an existing model. | — |
| What did you build and what was assisted? | Answer honestly: name the libraries (FastAPI, SQLAlchemy, pgvector, fastembed, React) and the AI coding assistance, and be ready to explain the core code yourself. | README "Acknowledgements" |

## Rehearsal log

| Date | Duration | What overran or broke | Change made |
|---|---|---|---|
| | | | |
