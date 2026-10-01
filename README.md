# Clause

Policy compliance intelligence: describe a business activity, get the applicable policy clauses, a structured assessment, the gaps and risks, and recommended actions, with every finding traceable to the exact clause, page and policy version behind it.

Capstone project. The demo corpus is a **fictional** organization's policies (Kestrel Mutual), not real policy, law or regulatory guidance. See [docs/data/corpus-decision.md](docs/data/corpus-decision.md).

## Status (30 September 2026)

| Area | State |
|---|---|
| Web app (`apps/web`) | Live mode (`VITE_API_MODE=http`) connects Cases, Policies and Ask a question to the API. The front door and the review, report, evaluation and settings screens are fixture prototypes; live mode labels them as such. |
| API (`services/api`) | Schema and migrations, PDF ingestion with source offsets, hybrid search, policy and source endpoints, cases, runs with progress events (SSE), clarification, cancel, and cited lookup answers. |
| Assessment workflow | Five stages in `app/workflow/`: retrieval, analysis, risk, validation, recommendation, then final checks. New runs account for retrieved requirement candidates and withhold clearance when coverage is unresolved. Scripted integration checks and live development runs use the same workflow. |
| Model-independent operation | Automatic fallback on model errors, or forced local operation with `LLM_MODE=offline`. Assessments collect source-linked user confirmations; policy questions return exact excerpts. Execution mode and reason are saved and shown in reports. |
| Evaluation | Latest development run: 12/13 statuses correct using Claude Sonnet 5.5, `analysis-v3` and the coverage gate; 0 unjustified compliant results across 9 eligible scenarios, 136/136 citations valid, and one cautious miss. Hybrid Recall@10 remains 0.839. That run predates the input check: today dev-012 (an "ignore your policies" request) is refused instead of assessed, so the same model outputs would score 11/13 ([analysis](docs/evaluation/analysis.md)). These are development results, not held-out accuracy; 20 held-out scenarios await label review. Earlier GPT-4o mini runs are preserved in the analysis. |

Live per-feature state: [docs/tasks/](docs/tasks/README.md). Plan: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Design system: [DESIGN.md](DESIGN.md).

For a plain-English walkthrough of the implementation, every module and code file, evaluation metrics, technology choices, and reviewer preparation, read either study guide: [docs/APP_GUIDE_CLAUDE.html](docs/APP_GUIDE_CLAUDE.html), or [docs/REVIEWER_GUIDE.html](docs/REVIEWER_GUIDE.html) with its [Markdown source](docs/REVIEWER_GUIDE.md). Both are single files that open offline in a browser.

### Evidence coverage (30 September 2026)

New assessments include an **Evidence Coverage Inspector**. It accounts for retrieved requirement candidates independently of the findings the model emits, shows their original text and PDF page, and distinguishes unassessed candidates from unconfirmed findings and validated exclusions. The counts are saved with the run, shown in its validation handoff, and included in JSON and printable reports.

Unresolved candidates block compliant and out-of-scope results; established breaches and conflicts still decide the result. A skipped clause is not invented as a violation or a missing business fact. Coverage uses requirement/exception classifications plus a small policy-derived catalog for obligations such as “are retained,” which the ingestion classifier otherwise labels general. It covers the retrieved bundle, not every policy obligation, and can increase cautious abstention when irrelevant candidates were retrieved. Older saved results say coverage was not recorded.

Evaluation reports now count **unjustified compliant results** across all scenarios whose acceptable labels exclude compliance, including conflict and missing-information cases, and report cautious misses and unresolved coverage. In the latest run, 12 of 13 assessments accounted for every retrieved candidate; one exclusion was disputed by validation. [Results](docs/evaluation/results-dev.md) and [analysis](docs/evaluation/analysis.md) record both coverage runs and the provider difference from 29 September. The enhancement roadmap and presentation priorities are in [docs/CAPSTONE_REVIEW_AND_IMPLEMENTATION_PLAN.md](docs/CAPSTONE_REVIEW_AND_IMPLEMENTATION_PLAN.md).

## Set up on a new machine

These steps take a fresh laptop to the running app. They were written on Windows 11 with PowerShell; where macOS or Linux differs, both commands are shown. Plan for about 15 minutes, most of it downloads.

### 1. Install the tools (once per machine)

| Tool | What it is for | Get it |
|---|---|---|
| Git | Clone the repository | <https://git-scm.com/downloads> |
| uv | Installs Python 3.12 and the API's dependencies, including the PostgreSQL 16 database with pgvector; you do not need to install Python, PostgreSQL or Docker yourself | Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"`<br>macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js 22 | Runs the web app; includes corepack, which provides the pinned pnpm 10 | <https://nodejs.org/en/download> (choose v22) |
| Google Chrome | Only for the browser tests (Playwright uses the installed Chrome) | <https://www.google.com/chrome/> |

Open a **new** terminal so the tools are on your PATH, then check them:

```bash
git --version
uv --version
node --version        # v22.x
corepack --version
```

On Windows, if PowerShell says "running scripts is disabled on this system" for `corepack` or `npm`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and open a new terminal.

### 2. Get the code

```bash
git clone https://github.com/PaulAndrew7/prodapt-capstone.git
cd prodapt-capstone
```

### 3. Create your `.env`

```powershell
Copy-Item .env.example .env      # Windows PowerShell
```

```bash
cp .env.example .env             # macOS/Linux
```

The defaults work as they are. `.env` is git-ignored, so the model key never travels with the repository; to use a model, add the key yourself (see [Connect the language model](#connect-the-language-model)).

### 4. Install the API and start the database

```bash
cd services/api
uv sync                                  # downloads Python 3.12 if needed; creates services/api/.venv
uv run python -m app.cli db-start        # the first run creates the database in var/postgres
```

PostgreSQL 16 with pgvector comes with the Python dependencies (the `pixeltable-pgserver` package), so there is nothing else to install. `db-start` runs it in the background on port **5433** (so it does not clash with another Postgres on 5432), listening on this computer only. It keeps running after the command returns, until you run `uv run python -m app.cli db-stop` or restart the computer; `db-status` shows whether it is running. The data lives in `var/postgres` and survives restarts.

### 5. Set up and start the API (terminal 1)

In the same terminal, still in `services/api`:

```bash
uv run python -m app.cli migrate         # creates the schema; the API never migrates on startup
uv run python -m app.cli seed-demo       # ingests the demo policy PDFs; the first run downloads a ~70 MB embedding model
uv run uvicorn app.main:app --port 8000
```

Leave it running. <http://localhost:8000/health/ready> should return `"status":"ok"` with `database`, `migrations` and `storage` all `ok` (`llm_provider` stays `not configured` until you add a key). The interactive API docs are at <http://localhost:8000/docs>.

### 6. Install and start the web app (terminal 2)

From the repository root:

```bash
corepack pnpm install            # answer Y if corepack asks to download pnpm
```

Then start Vite in live mode, so the app talks to your API:

```powershell
$env:VITE_API_MODE="http"; corepack pnpm --dir apps/web dev      # Windows PowerShell
```

```bash
VITE_API_MODE=http corepack pnpm --dir apps/web dev              # macOS/Linux
```

Open <http://localhost:5173> for the front door and <http://localhost:5173/app> for the application. Vite proxies `/api` and `/health` to port 8000.

Without `VITE_API_MODE`, the web app runs on built-in fixture data and needs neither the API nor the database, which is handy for a quick look at the interface.

### 7. Every time after that

The install, migrate and seed steps are one-offs. To start working again:

1. Terminal 1: `cd services/api`, then `uv run python -m app.cli db-start` (it says so if the database is already running) and `uv run uvicorn app.main:app --port 8000`.
2. Terminal 2: the live-mode Vite command from step 6.

After a `git pull`, run `uv sync`, `uv run python -m app.cli migrate` and `corepack pnpm install` again; each does nothing if nothing changed. `seed-demo` is also safe to repeat, since it skips policy versions that are already loaded.

To stop, press Ctrl+C in both terminals and run `uv run python -m app.cli db-stop` in `services/api`. To start over with an empty database, run `db-stop`, delete the `var/postgres` folder, then repeat steps 4 and 5.

## Connect the language model

Configuration lives in environment variables read from `.env` at the repository root. Production refuses development defaults (database URL, session secret, demo auth).

A language model enables automatic narrative interpretation and synthesized policy answers. The project runs on **Claude through the Anthropic API**, with structured outputs. Claude Sonnet 5.5 produced the latest evaluation results; Claude Haiku 4.5 is cheaper and works for testing (its results are not comparable with the Sonnet numbers). Set these in `.env`, then restart the API:

```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-5-5   # or claude-haiku-4-5
LLM_EFFORT=low                # thinking effort; remove this line for claude-haiku-4-5, which rejects it
LLM_API_KEY=sk-ant-...        # read by the API only, never sent to the browser
```

The organizers' gateway serves **GPT-4o mini** in the OpenAI chat-completions format. The project first ran on it (29 September; those runs are in the [analysis](docs/evaluation/analysis.md)), and it remains supported:

```bash
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://keygateway1.arshnivlabs.com/v1   # requests go to <base>/chat/completions
LLM_API_KEY=...            # your lab key; read by the API only, never sent to the browser
LLM_JSON_MODE=json         # the gateway accepts response_format "json" as a plain string only
LLM_MAX_OUTPUT_TOKENS=500  # the gateway rejects anything higher
LLM_TEMPERATURE=0          # the gateway defaults to 1.0; 0 keeps verdicts steadier
```

Leave `LLM_MODEL` unset for the gateway: it picks the model itself (it always serves `gpt-4o-mini`), so no model name is sent. The gateway has no JSON-schema mode, so each stage's schema goes in the system message and every reply is validated in the API, with one repair request at most. An analysis reply can run past the 500-token cap; the client then trims it to its last complete line, asks the model to continue from there (up to three times) and joins the pieces before validating.

Another OpenAI-format gateway also works: set `LLM_BASE_URL`, `LLM_MODEL` if it needs a model name, and optionally `LLM_API_KEY_HEADER=api-key` (key in a named header instead of Bearer), `LLM_JSON_MODE=json_schema|json_object` and `LLM_TEMPERATURE`.

Then confirm the connection with one small request before running an assessment:

```bash
cd services/api
uv run python -m app.cli check-model     # prints the served model, token counts and time, or the error
```

With the default `LLM_MODE=auto`, missing or incomplete model settings select local review. Authentication, rate-limit, connection, timeout and unusable-response errors also switch the current run to local review. Each budgeted model call, including continuations, has a 20-second timeout by default (`LLM_CALL_TIMEOUT_SECONDS`), bounded by the run deadline. A schema repair is a separate budgeted call with the same cap. After switching, clarification resumes use the local engine; a new run can try the provider again. `LLM_MODE=required` retains strict configuration and failed-run behavior for provider diagnostics and model-only evaluation.

### Run without an LLM

Set these in `.env` and restart the API:

```bash
LLM_MODE=offline
EMBEDDINGS_ENABLED=false    # optional: lexical search only, no embedding-model download
```

`offline` skips provider-client construction even if a key is configured. The seeded PostgreSQL database and policy PDFs are still required. Browse policies, search, source links, conversation, progress, saved cases and reports continue to work.

An assessment retrieves the same dated policy evidence and asks for explicit dispositions in batches of three: **applies and satisfied**, **applies and breached**, or **does not apply**. Each check links to its original clause. “I don't know” preserves unknown; **Finish with remaining checks unknown** saves a report immediately. Confirmations persist across batches. Unknown checks prevent clearance, and local conclusions explicitly depend on the user's confirmations. Source/choice checks run in code; applicability, exceptions and precedence require human interpretation. Local results remain unreviewed and carry no model evidence score.

**Ask a question** returns ranked, exact source excerpts and PDF links in local mode. It labels these as excerpts requiring interpretation. The UI, trace, JSON and print report record the execution mode and fallback reason. Historical cases without metadata retain their original format.

Removing or blanking `LLM_API_KEY` and restarting the API is enough to select local review with the default `LLM_MODE=auto`; no replacement key is needed. `LLM_MODE=required` intentionally disables that fallback. Local search uses PostgreSQL full-text ranking (not BM25), and optional local dense embeddings. If the embedding model cannot load or a query embedding fails, search automatically continues with its keyword results. After a model-load failure, restart the API to retry dense search. The database and ingested policy documents must still be available.

### Unrelated requests

Policy questions and assessments now pass a local relevance check before any generation or local checklist. It rejects obvious instruction overrides, forced verdicts, trivia such as weather questions, and input without meaningful overlap with a retrieved policy. Unsupported questions receive a fixed explanation with no citations; assessments stop with a non-retryable `request_out_of_scope` or `request_redirected` error and no compliance result. The case screen asks for a relevant request rather than offering to retry the same input. Clarification replies are also checked for obvious redirects and trivia.

Negative business facts such as missing approval or a data breach remain valid inputs. The check uses English word overlap and common request patterns, not sentiment. It is deliberately conservative: unfamiliar paraphrases may need rephrasing, and it is not a complete prompt-injection defence. Existing evaluation scores predate this admission check; adversarial and out-of-corpus requests can now be declined before an assessment is produced.

The design, acceptance checks and implementation record are in [the fallback plan](docs/OFFLINE_FALLBACK_IMPLEMENTATION_PLAN.md).

## Sample usage

```bash
curl -s localhost:8000/health/ready
curl -s localhost:8000/api/v1/policies
curl -s localhost:8000/api/v1/policy-versions/ds_v1            # clauses of the Customer Data Sharing Policy v1
curl -s -X POST localhost:8000/api/v1/search -H 'content-type: application/json' \
  -d '{"question": "Can we send customer records to an analytics vendor without data owner approval?"}'
curl -sL "localhost:8000/api/v1/policy-versions/ds_v1/source?page=2" -o ds_v1.pdf   # the cited original
```

For either model-assisted or local operation:

```bash
# A cited answer to a policy question
curl -s -X POST localhost:8000/api/v1/lookup -H 'content-type: application/json'   -d '{"question": "Who must approve sharing customer data with a vendor?"}'

# An assessment: create a case, start a run, follow progress, read the result
CASE=$(curl -s -X POST localhost:8000/api/v1/cases -H 'content-type: application/json'   -d '{"text": "We plan to send customer records to an external analytics vendor. We have not obtained written data-owner approval. I do not know whether the vendor review is complete.", "business_area": "Marketing analytics", "as_of": "2026-09-26"}' | jq -r .id)
RUN=$(curl -s -X POST localhost:8000/api/v1/cases/$CASE/runs -H 'Idempotency-Key: demo-1' | jq -r .run_id)
curl -sN localhost:8000/api/v1/runs/$RUN/events          # progress; stays open while waiting for answers (Ctrl+C)
curl -s localhost:8000/api/v1/runs/$RUN | jq '.state, .pending_questions'
curl -s -X POST localhost:8000/api/v1/runs/$RUN/resume -H 'content-type: application/json'   -d '{"answers": {"q_1": null}}'                        # null means "I don't know"
curl -s localhost:8000/api/v1/runs/$RUN | jq '.assessment.status, .assessment.findings'
curl -s localhost:8000/api/v1/runs/$RUN | jq '.assessment.confidence, [.assessment.findings[].confidence.score]'
```

Use question IDs returned in `pending_questions` when resuming. In local mode, complete remaining checks as unknown with `POST /api/v1/runs/{run_id}/resume` and `{"answers": {}, "finish_local_review": true}`. Otherwise, submit the exact offered choices or `null` and repeat for subsequent batches.

Model-assisted findings, results and lookup answers include a `confidence` object: a 0-100 evidence score, a band (high >= 80, medium >= 50, low) and the factors that produced it. It is computed in code from the run's checks and is not a probability; see [decisions.md](docs/architecture/decisions.md#results). Local review uses `confidence: null` because interpretation depends on the user's confirmations.

`uv run python -m app.cli search "who approves temporary production access"` prints ranked clauses with their lexical and dense ranks. OpenAPI docs: http://localhost:8000/docs.

## Evaluation

```bash
cd services/api
uv run python -m app.cli evaluate --split dev                   # retrieval, plus assessments if a model is set
uv run python -m app.cli evaluate --split dev --retrieval-only  # no model calls
```

The command creates and seeds a separate `<database>_eval` database, so evaluation cases never appear in the demo. It writes `docs/evaluation/results-<split>.md`, including accuracy per confidence band once assessments run (currently [results-dev.md](docs/evaluation/results-dev.md)) and a raw JSON file; the written failure analysis is in [docs/evaluation/analysis.md](docs/evaluation/analysis.md). Answer keys in `data/evaluation/` are never indexed or put into prompts.

## Checks

```bash
cd services/api
uv run ruff check app tests ../../scripts && uv run mypy app
uv run pytest                     # DB tests use a separate <db>_test database; skipped if Postgres is down
uv run python -m app.cli export-openapi --check

corepack pnpm --dir apps/web typecheck
corepack pnpm --dir apps/web test
corepack pnpm --dir apps/web exec playwright test
```

CI (`.github/workflows/ci.yml`) runs the same checks plus a clean migration, corpus reproducibility and a demo seed.

## Architecture

![System architecture](docs/architecture/architecture-system.jpg)

One FastAPI process serves the API and runs each assessment as a background task: retrieval, compliance analysis, risk, validation and recommendation, then final checks that decide the status with ordered rules and retrieved-candidate coverage. Search runs inside PostgreSQL with local embeddings; the external runtime calls are to the configured model provider (the organizers' gateway or Anthropic). The full diagram (system and workflow pages) is [docs/architecture/architecture.pdf](docs/architecture/architecture.pdf), and the decisions and tradeoffs are in [docs/architecture/decisions.md](docs/architecture/decisions.md).

## Limitations

- **Development-set results only so far.** The latest 12/13 result uses Claude Sonnet 5.5 and a checklist tuned on the development split, and predates the input check (11/13 with today's code, since dev-012 is now refused). It cannot be attributed solely to the gate or compared directly with earlier GPT-4o mini results. Held-out labels still need owner review before the final run. A model can still misinterpret an accounted-for clause or choose unsupported policy precedence; coverage does not prevent those errors. Results vary between runs; see [analysis.md](docs/evaluation/analysis.md).
- **500-token replies on the gateway.** The organizers' gateway caps each reply at 500 tokens, so long analysis replies are continued with follow-up requests. That costs time, and a continuation that does not join cleanly fails validation and uses the stage's one repair request.
- **Small, fictional evaluation.** 13 development and 20 held-out scenarios on an invented corpus; results describe this corpus, not general accuracy. No held-out case expects a policy conflict, because the corpus's only two-policy conflict is in the development split.
- **Valid citations are not correct interpretations.** Validation proves a quoted passage exists in a retrieved clause; whether it supports the conclusion relies on a model check and human review.
- **Local review needs human interpretation.** It checks stored sources and explicit dispositions; it does not parse arbitrary narrative, independently determine applicability, or resolve policy exceptions and precedence. Unknown checks prevent clearance, and local results remain unreviewed.
- **Retrieval misses some clauses.** Purpose-limitation rules are rarely in the top ten because scenarios describe what is sent, not why ([analysis](docs/evaluation/analysis.md)).
- **One process, one user.** A restart fails an in-flight run (completed results stay saved). Demo authentication maps every request to one seeded user; this is not a public multi-user service.
- **Digital PDFs only.** No OCR or DOCX. The demo corpus is ingested from the command line; an admin can upload a further PDF policy or version in the app (Policies → Manage), review its extracted clauses and then publish it.
- **Prototype screens.** Review, reports, evaluation lab and settings are fixture prototypes and are labelled as such in live mode.

## Troubleshooting

Evaluation rejects non-positive `--limit` values and unreviewed held-out labels before database setup. Disputed records are excluded. Each new run preserves a uniquely named raw JSON file and records scenario/corpus hashes; the Markdown report remains the latest result. See [evaluation input/review rules](data/evaluation/README.md).

Model requests have no hidden SDK retries. Failed requests count against the attempt budget, and late replies are rejected. Automatic mode switches to local review after a provider failure; a fresh run can try the provider again. Required mode records the failure and needs an explicit retry. Gateway URLs must use HTTP(S) with no embedded credentials, query or fragment; keys stay in `LLM_API_KEY`.

| Symptom | Likely cause and fix |
|---|---|
| `db-start` says port 5433 is already in use | Another program holds the port, often the Docker database from an earlier version of this setup (stop or delete the `clause-db-1` container in Docker Desktop) or another Postgres. Stop it, or change the port in `DATABASE_URL` in `.env`. |
| `db-start` says the database did not start | The message ends with the last lines of `var/postgres.log`. If the log says the data directory is from another PostgreSQL version or is damaged, and you do not need its data, delete `var/postgres` and run `db-start` again. |
| Search fails with "server closed the connection unexpectedly" and `var/postgres.log` shows `terminated by exception 0xC000001D` | The pgvector build uses CPU instructions this computer lacks. Run `uv sync`: `pyproject.toml` pins `pixeltable-pgserver` 0.5.1 because 0.6.0 crashes on CPUs without AVX-512. |
| Port 8000 is already in use | Stop the other program, or start the API with another `--port` (for example 8001) and start Vite with `VITE_API_PROXY=http://localhost:8001` as well. |
| `uv`, `node` or `corepack` is not recognized | Open a new terminal after installing. If `corepack` is missing (Node 25 and later no longer bundle it), run `npm install -g corepack`. |
| PowerShell: "running scripts is disabled on this system" | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then open a new terminal. |
| `seed-demo` fails while downloading the embedding model | The first run needs internet access to fetch BAAI/bge-small-en-v1.5 into `var/models`. Retry on a working connection; set `EMBEDDINGS_ENABLED=false` in `.env` for lexical-only search. |
| `curl localhost:8000/health/ready` reports `database: unavailable` | The database is not running (for example after a restart of the computer): `uv run python -m app.cli db-start` in `services/api`. |
| `migrations: pending` | Run `uv run python -m app.cli migrate`; the API never migrates on startup. |
| Search returns nothing, or `demo_not_seeded` | Run `uv run python -m app.cli seed-demo`. The first run downloads the ~70 MB embedding model into `var/models`. |
| `model_not_configured` when starting a case or asking a question | In `LLM_MODE=required`, configure the provider and restart the API. Use `LLM_MODE=auto` or `offline` to enable local operation. `check-model` is a provider diagnostic and still requires a model. |
| `check-model` fails with `model_bad_request` | The gateway rejected the request format. For the organizers' gateway set `LLM_JSON_MODE=json` and `LLM_MAX_OUTPUT_TOKENS=500`; for another gateway without JSON-schema support, `LLM_JSON_MODE=json_object`. |
| `check-model` fails with `model_auth` | Check the key (for `anthropic`, an `sk-ant-` key from the Anthropic Console); if the gateway expects it in a named header rather than `Authorization: Bearer`, set `LLM_API_KEY_HEADER` (for example `api-key`). |
| `check-model` fails with `model_not_found` | `LLM_BASE_URL` should end before `/chat/completions` (for the organizers' gateway, `.../v1`); if `LLM_MODEL` is set it must be the gateway's exact alias. |
| A run shows `interrupted` | The API restarted during that run. Start a new run; completed results are unaffected. |
| The web app shows fixture data | Start Vite with `VITE_API_MODE=http` so `/api` is proxied to the API. |

## Acknowledgements

Libraries and assets are listed with their licenses in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The runtime model is Claude Sonnet 5.5 (Anthropic) through the Anthropic API, with Claude Haiku 4.5 as a cheaper option; GPT-4o mini (OpenAI) through the project organizers' gateway is a supported alternative. None is trained or fine-tuned here. The embedding model is BAAI/bge-small-en-v1.5. Parts of the code and documentation were written with the help of an AI coding assistant (Claude Code).

## Layout

```text
apps/web/            React + Vite frontend (see apps/web/README.md)
services/api/        FastAPI service, ingestion, retrieval, workflow (app/workflow), migrations, tests
packages/contracts/  OpenAPI export and shared JSON fixtures used by both sides
data/demo/           Fictional policy sources (Markdown), generated PDFs, manifest with hashes
data/evaluation/     Hand-labelled scenarios; never indexed
scripts/             build_demo_corpus.py (regenerates PDFs and the manifest)
docs/                architecture (diagram, decisions, ADRs), data decisions, design, evaluation, task records, presentation
```
