# Evidence coverage implementation — 30 September 2026

Implemented the first presentation priority from the [capstone review plan](../CAPSTONE_REVIEW_AND_IMPLEMENTATION_PLAN.md): make omitted retrieved requirements visible and prevent incomplete clearance.

## Delivered behavior

- Every retrieved requirement/exception candidate needs a validated finding or validated exclusion. A policy-derived catalog also includes obligations the ingestion classifier labels general, such as “are retained.” Definition clauses remain context. A quote used by another finding does not account for the quoted clause's own requirement.
- Coverage rows retain clause IDs, policy/version, original stored text, PDF page, retrieval reason, disposition and finding IDs. The dated evidence bundle determines which versions are inspected.
- Omissions and disputed dispositions block compliant and out-of-scope outcomes. Established breaches and conflicts retain precedence. Unknown findings count as assessed, while their unknown facts still prevent compliance.
- The existing analysis stage receives a compact candidate checklist (`analysis-v3`). Explicit exclusions survive an `in_scope=false` response and reach validation.
- Coverage is persisted with assessments and validation handoffs, appears above the result tabs, and is included in JSON and complete printable reports. Native disclosures work by keyboard on desktop and mobile. Older saved assessments show “coverage not recorded.” No migration or extra model stage was added.
- UI labels call the existing confidence metric an **evidence score**. A result withheld for unresolved coverage reports incomplete evidence checks rather than borrowing a met finding's score.
- Evaluation reports add unjustified compliance across all non-clearance labels, cautious misses and unresolved coverage. Raw development runs remain preserved.
- Browser tests run their fixture server on **5174**, independently of the live app on 5173.

## Verification

| Check | Result |
|---|---|
| Full backend suite, including PostgreSQL integration | 235 passed |
| Backend Ruff / mypy | Passed / 42 source files passed |
| Shared fixtures and OpenAPI export freshness | Passed |
| Frontend TypeScript / Vitest | Passed / 36 tests across 8 files |
| Frontend production build | Passed |
| Browser suite | 24 passed; desktop/mobile, keyboard, source links, print, existing flows and accessibility |
| Visual inspection | Desktop and mobile screenshots inspected; no horizontal overflow |
| Real-model HTTP smoke check | Passed: create/start, clarification with unknown answers, completion, saved case response, source redirect and SSE coverage counts |

Existing warnings: Alembic's `prepend_sys_path` configuration uses a deprecated separator fallback; the frontend build reports a large bundle. These do not indicate a failed check.

The regular local API was stopped at the time of the HTTP check. A temporary server on 8001 used the separate evaluation database and was stopped afterward. Its v2 transfer assessment completed with all 10 retrieved candidates accounted for and the retention period still unknown; no compliant result was returned. Debug artifacts are in `tmp/coverage-smoke/` and are not a new benchmark report or a demo-database record.

## Real-model development measurements

Both runs used the project's configured `anthropic:claude-sonnet-5-5`. The model configuration and evaluation labels were not changed by this batch. Evaluation used its separate database; the held-out split was not read or run.

| Measurement | Gate + analysis-v2 | Gate + checklist, analysis-v3 |
|---|---|---|
| Final status correct | 9/13 | 12/13 |
| Unjustified compliant | 0/9 | 0/9 |
| Cautious misses | 3 | 1 |
| Incomplete coverage runs | 13/13 | 1/13 |
| Unresolved candidates | 74 | 1 |
| Citation validity | 65/65 | 136/136 |
| Labelled requirements matched | 30/44 | 32/44 |
| Completed / failed | 13 / 0 | 13 / 0 |
| Median latency | 14.2 s | 21.4 s |

Raw runs: [gate only](../evaluation/raw/dev-2026-09-30-21baf2dcdab74ab3986c1f51543b0e8a.json), [with checklist](../evaluation/raw/dev-2026-09-30-c85bcc97d9c04b4eb7c318c0961a9441.json). Latest generated report: [results-dev.md](../evaluation/results-dev.md).

The v2 retention omission now produces a validated unknown finding. The remaining dev-002 miss is a cautious withholding: analysis excluded the legally-required-transfer exception, but validation disputed that exclusion because the scenario does not explicitly say no law requires the transfer. Coverage correctly exposes this disagreement; it does not solve interpretation errors. The final checklist run still matches only 32/44 requirement labels despite 12/13 final statuses.

These are development measurements after prompt adjustment, not general accuracy. The provider differs from the 29 September GPT-4o mini baseline. Manual evidence-support review and owner-reviewed held-out evaluation are pending. The older gateway configuration has not been rebenchmarked with this larger checklist output.

## Demonstrating the result

Create a fresh live assessment, open **Evidence coverage**, expand a candidate and follow **Open original PDF**. Show that an assessed unknown differs from an unassessed candidate. For a stable presentation, retain a clearly identified previous real run and its exported report as fallback. Historical runs are not backfilled from their findings.

Kafka and the remaining roadmap features are not implemented in this batch.
