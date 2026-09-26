# Clause

Policy compliance intelligence: describe a business activity, get the applicable policy clauses, a structured assessment, the gaps and risks, and recommended actions, with every finding traceable to the exact clause, page and policy version behind it.

Capstone project. The demo corpus is a **fictional** organization's policies (Kestrel Mutual), not real policy, law or regulatory guidance. See [docs/data/corpus-decision.md](docs/data/corpus-decision.md).

## Status (26 September 2026)

| Area | State |
|---|---|
| Web app (`apps/web`) | Front door and app pages built against fixtures. Policy library and detail also run against the live API. |
| API (`services/api`) | FastAPI service: schema and migrations, PDF ingestion into clauses with source offsets, hybrid search, policy/source endpoints, health checks. |
| Assessment workflow (five agents) | Not started (F07–F11). The app's case workspace still replays fixtures. |
| Evaluation | 13 hand-labelled development scenarios; no harness or measured results yet (F14). |

Live per-feature state: [docs/tasks/](docs/tasks/README.md). Plan: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Design system: [DESIGN.md](DESIGN.md).

## Run it locally

Prerequisites: Docker, [uv](https://docs.astral.sh/uv/), Node 22 with corepack.

```bash
# 1. Database (Postgres 17 + pgvector on host port 5433)
docker compose up -d db

# 2. API
cd services/api
uv sync
uv run python -m app.cli migrate        # explicit; the API never migrates on startup
uv run python -m app.cli seed-demo      # ingests data/demo PDFs; first run downloads the ~70 MB embedding model
uv run uvicorn app.main:app --port 8000

# 3. Web (from the repo root, in another terminal)
corepack pnpm install
corepack pnpm --dir apps/web dev                          # fixture mode: http://localhost:5173
VITE_API_MODE=http corepack pnpm --dir apps/web dev       # live mode: /api is proxied to :8000
```

Or run the API in a container: `docker compose up --build`, then `docker compose run --rm api python -m app.cli migrate` and `docker compose run --rm api python -m app.cli seed-demo`.

Configuration lives in environment variables; copy [.env.example](.env.example) to `.env` to override. Production refuses development defaults (database URL, session secret, demo auth).

## Sample usage

```bash
curl -s localhost:8000/health/ready
curl -s localhost:8000/api/v1/policies
curl -s localhost:8000/api/v1/policy-versions/ds_v1            # clauses of the Customer Data Sharing Policy v1
curl -s -X POST localhost:8000/api/v1/search -H 'content-type: application/json' \
  -d '{"question": "Can we send customer records to an analytics vendor without data owner approval?"}'
curl -sL "localhost:8000/api/v1/policy-versions/ds_v1/source?page=2" -o ds_v1.pdf   # the cited original
```

`uv run python -m app.cli search "who approves temporary production access"` prints ranked clauses with their lexical and dense ranks. OpenAPI docs: http://localhost:8000/docs.

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

## Layout

```text
apps/web/            React + Vite frontend (see apps/web/README.md)
services/api/        FastAPI service, ingestion, retrieval, migrations, tests
packages/contracts/  OpenAPI export and shared JSON fixtures used by both sides
data/demo/           Fictional policy sources (Markdown), generated PDFs, manifest with hashes
data/evaluation/     Hand-labelled scenarios; never indexed
scripts/             build_demo_corpus.py (regenerates PDFs and the manifest)
docs/                architecture ADRs, data decisions, design, feature task records
```
