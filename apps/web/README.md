# Clause web

React 19 + TypeScript + Vite frontend for Clause. Design direction and decisions: `docs/design/FRONTEND_PLAN.md` (plan) and `DESIGN.md` (built system, written after the finish review).

## Run

```bash
corepack pnpm install          # from the repo root or apps/web
corepack pnpm --dir apps/web dev   # http://localhost:5173
```

- `/` is the public front door (Lenis, parallax, Three.js hero, product exhibits).
- `/app` is the application (cases, policies, reviews, reports, evaluation, settings).

## Data modes

| `VITE_API_MODE` | Behavior |
|---|---|
| unset (default) | `FixtureApi` plays authored scenarios with realistic timing. Every app screen shows a "Fixture data" tag. No model provider is called. |
| `http` | `HttpApi` calls the FastAPI routes in IMPLEMENTATION_PLAN.md §5.4 (same origin, SSE for run events). The dev server proxies `/api` and `/health` to `http://localhost:8000` (override with `VITE_API_PROXY`). As of 26 Sep 2026 the policy library and policy detail work live; cases, runs and lookup need F06/F07+. |

All policies, people and cases in `src/fixtures/` are fictional (Kestrel Mutual). The front-door exhibits always render fixture data, even in `http` mode.

`src/fixtures/contractFixtures.ts` generates the shared JSON in `packages/contracts/fixtures/` that the backend tests validate. After changing the vendor fixtures run `corepack pnpm --dir apps/web contracts:fixtures`; `pnpm test` fails on drift.

## Check

```bash
corepack pnpm --dir apps/web typecheck
corepack pnpm --dir apps/web test          # Vitest (avatar controller)
corepack pnpm --dir apps/web exec playwright test   # flows, reduced motion, axe on 11 routes (uses installed Chrome)
corepack pnpm --dir apps/web build
```

Screenshot helpers used during design review live in `scripts/` (`flow.mjs`, `pages.mjs`, `sections.mjs`, `scrollshots.mjs`, `stills.mjs`). `stills.mjs` regenerates the fallback images in `public/` from the live 3D renders.

## Structure

- `src/lib/api`: the `ComplianceApi` seam (`fixtureApi.ts`, `httpApi.ts`) and contract types mirroring plan §5.
- `src/lib/events/runStore.ts`: deduplicating run-event store; workspace, stage track and avatar all read from it.
- `src/features/cases`: case workspace (P04), composer, index.
- `src/features/policies`: library with grounded lookup, policy detail with citation deep links and version compare.
- `src/features/front-door`: front door, exhibits (real components at fixed logical size), `PolicyStack` 3D scene.
- `src/features/avatar`: pure controller (`controller.ts`, unit-tested) and the procedural 3D figure.
