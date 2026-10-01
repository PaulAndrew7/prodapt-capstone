# Notes for Claude Code

Clause is a capstone project: a policy-compliance assistant. FastAPI backend in `services/api` (five-stage workflow in `app/workflow/`), React + Vite frontend in `apps/web`, PostgreSQL 16 + pgvector run locally from a Python package. The corpus (Kestrel Mutual) is fictional. Start with `README.md`; the study guides are `docs/APP_GUIDE_CLAUDE.html` (written by Claude) and `docs/REVIEWER_GUIDE.html` (written by Codex, built from `docs/REVIEWER_GUIDE.md` by `docs/build_reviewer_guide.py`). Files with a `CLAUDE` suffix are Claude's; Codex also edits this repository.

## Setting up a new machine

Follow README "Set up on a new machine" (Windows 11 + PowerShell is the main target). In short:

1. Tools: Git, uv, Node 22 (corepack), Chrome for browser tests. No Python, PostgreSQL or Docker install is needed.
2. `Copy-Item .env.example .env`. The owner adds the model key to `.env` themselves: never ask for the key in chat and never print `.env` without redacting `LLM_API_KEY`. Model settings: `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-sonnet-5-5` with `LLM_EFFORT=low` (the published results), or `LLM_MODEL=claude-haiku-4-5` with no `LLM_EFFORT` (cheaper; Haiku rejects the effort setting).
3. In `services/api`: `uv sync`, `uv run python -m app.cli db-start`, `migrate`, `seed-demo` (first run downloads a ~70 MB embedding model), `check-model`.
4. API: `uv run uvicorn app.main:app --port 8000`. Web, from the repo root: `corepack pnpm install`, then `$env:VITE_API_MODE="http"; corepack pnpm --dir apps/web dev` and open http://localhost:5173/app.
5. Saved cases are not in git (they live in `var/postgres`), so a new machine has none. Before a demo, run one assessment through the UI (Cases → New case → "Share data with a new vendor" sample) so there is a completed case to fall back on.

## Checks (what CI runs, plus browser tests)

```bash
cd services/api
uv run ruff check app tests ../../scripts && uv run ruff format --check app tests ../../scripts
uv run mypy app
uv run python -m app.cli migrate && uv run alembic check
uv run python -m app.cli export-openapi --check
uv run pytest                      # needs db-start; creates and uses a separate clause_test database

corepack pnpm --dir apps/web typecheck
corepack pnpm --dir apps/web test
corepack pnpm --dir apps/web build # the >500 kB chunk warning for the 3D scene is expected
corepack pnpm --dir apps/web e2e   # Playwright with the installed Chrome, fixture mode; CI skips these
```

After changing API models, regenerate the contract with `uv run python -m app.cli export-openapi` (the check fails otherwise). After editing `docs/architecture/diagram/architecture.html`, re-export with `corepack pnpm --dir apps/web export:architecture`.

## Rules and quirks

- Use `corepack pnpm`, not a global pnpm.
- `pixeltable-pgserver` is pinned to 0.5.1 on purpose: 0.6.0's pgvector crashes on CPUs without AVX-512. Do not upgrade it.
- The database listens on port 5433; its data is in `var/postgres` at the repository root and its log in `var/postgres.log`. After a reboot, run `db-start` again.
- Keep LF line endings (`.gitattributes` has `eol=lf`). When a Python script writes files on Windows, open them with `newline=''`.
- In Git Bash, set `MSYS_NO_PATHCONV=1` before commands that take `/app/...` routes, or the path gets rewritten.
- Vite moves to port 5174 if 5173 is taken.
- Never read, run or tune on the held-out split (`data/evaluation/test/`) until the owner has reviewed and frozen its labels; `evaluate --split test` refuses unreviewed labels.
- `evaluate --split dev` makes real model calls on the owner's key. Ask before running it.
- With `LLM_MODE=auto` (default), a model error or a call over `LLM_CALL_TIMEOUT_SECONDS` (default 20) switches the run to local review. If Sonnet runs keep falling back on timeouts, raise it (for example 45).
- Do not commit `.env`, `var/`, `tmp/` or the course brief PDF.
