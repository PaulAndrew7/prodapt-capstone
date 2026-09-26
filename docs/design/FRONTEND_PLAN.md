# Frontend plan: Clause (Highlighter direction, v2)

## Context

`D:\coding\capstone` contains only `IMPLEMENTATION_PLAN.md` and the PDF brief. No code exists yet. The project is a policy-compliance intelligence system: FastAPI backend, five runtime agents, React frontend, 5-day deadline. The PDF's Task 4 requires a front end showing applicable policies, clauses, citations, the assessment, gaps/risks and recommended actions.

**What the user asked for:**
- A clean, modern, big/bold, awwwards-level frontend.
- Lenis smooth scroll, parallax, and Three.js where it earns its place.
- Notion-style product storytelling: every feature claim sits beside an exhibit of the real app doing it.
- Big, bold fonts that don't look AI-generic.

Section 12 of the existing plan (warm cream canvas, serif, deep green) is replaced.

**Confirmed decisions:**
1. **Front door plus app.** A scroll-driven public page at `/`, with the app under `/app/*`. The front door replaces the plain P01 login and opens the panel demo.
2. **Highlighter direction.** Cool paper, ink-black type, one fluorescent highlighter mark. The signature interaction is the highlighter sweeping across the exact clause words behind a finding.

**Design read:** a front door (impeccable *Persuade* mode) that sells an authenticated compliance-decision workspace (*Operate* mode). Audience: compliance analysts and the capstone panel. Language: big, bold, clean and modern, in the style of a product website. Stack: Vite, React, Tailwind v4 tokens, Motion, Lenis, React Three Fiber.

**Dials (VARIANCE / MOTION / DENSITY):**
- Front door: 8 / 8 / 3
- App: 5 / 4 / 6

**Scope split for motion:** Lenis, parallax and the 3D hero apply to the front door only. The app keeps native scroll. The case workspace has several independent scroll panes (conversation, matrix, evidence drawer), where smooth-scroll interpolation slows precise reading. The only 3D in the app is the avatar.

## Direction contract

This goes verbatim as the first HTML comment in `apps/web/index.html` `<body>`.

- **THESIS:** Every verdict is pinned to the exact words that justify it. The design refuses the dark AI dashboard with a score dial, and the cream editorial serif workspace.
- **OWN-WORLD:**
  - Surfaces: cool paper `#F4F6F5`, sheets `#FBFCFB`, ink `#111413`.
  - Accent: one fluorescent mark `#DDFF3C`, used only as a fill behind ink.
  - Structure: 2px ink rules, square corners, no shadows. Depth comes from parallax layers, not blur.
  - Type: Clash Display for headlines and verdicts, Switzer for the working UI.
- **STORY:** A pile of policies resolves into one highlighted clause. The real product then shows how to describe an activity, answer only the questions that matter, get a verdict, and open the evidence behind it.
- **FIRST VIEWPORT:**
  - Left: a two-line headline "Every verdict, / pinned to its clause.", with the mark sweeping "pinned to its clause." on load. Below it, an 18-word subtext and the CTAs "Enter demo" (mark fill) and "See how it works".
  - Right, bleeding off the edge: a Three.js stack of policy sheets. Scrolling brings §4.2 forward and highlights it.
- **FORM:** Highlighter. The user pinned it via a structured question on 25 Sep 2026, so it overrides the concept-seed roll.
- **FINISH:** "unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance"

## Design system (`apps/web/src/styles/tokens.css` → Tailwind v4 `@theme`)

**Color.** Restrained: neutrals plus the mark. Status is always shown with text and an icon, never by color alone.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#F4F6F5` | `#0E1110` | Page ground |
| `--sheet` | `#FBFCFB` | `#151918` | Documents, exhibits, drawer, composer |
| `--ink` | `#111413` | `#EDF1EE` | Text, primary buttons, 2px rules, focus ring |
| `--ink-2` | `#4A524E` | `#A3ADA8` | Secondary text (≈7:1 on paper) |
| `--rule` | `#D5DAD7` | `#2A302D` | Hairlines |
| `--mark` | `#DDFF3C` | `#DDFF3C` | Evidence spans, selection, the one accent CTA per view. Text on it is always `#111413`. |
| `--violated` / `--unknown` / `--met` / `--muted` | `#B42318` / `#8A5A00` / `#1D6B45` / `#6B726E` | `#FF8A7A` / `#F2B84B` / `#6FD39B` / `#8A938E` | Status words and icons |

Conflict status is ink plus a diagonal-hatch mark. The mark is never used for text, borders or focus, because it fails 3:1 contrast on paper. Focus ring: 2px ink with a 2px offset.

**Type.** Big, bold, and not an AI default. Both faces come from Fontshare under the ITF Free Font License. They are self-hosted as woff2 in `src/assets/fonts/` via `@font-face` with `font-display: swap`. The hero weight is preloaded, and licenses are recorded in `THIRD_PARTY_NOTICES.md`.

- **Display: Clash Display, 600/700.**
  - Front-door H1: `clamp(48px, 7.2vw, 112px)`, tracking −0.035em, leading 1.0.
  - Section H2: `clamp(36px, 4.6vw, 72px)`.
  - Verdict headline in the app: 56–96px.
  - App page titles: 40px.
  - Descender reserve: leading ≥1.05 plus `pb-2` wherever a mask-reveal clips lines.
- **UI and body: Switzer Variable, 100–900.** App scale in fixed rem: 12 / 14 / 16 body / 20 / 24 / 32. Tabular numerals are used for clause refs, versions and dates; this needs verifying during the Phase 0 proof. Measure: 68ch.
- **Emphasis:** the highlighter mark, never a second family or italics.
- **Phase 0 font proof:** render the hero, a verdict and a workspace row in three pairings at 1440 and 390 wide, then screenshot them for the user to confirm before building further:
  1. Clash Display + Switzer (primary)
  2. Cabinet Grotesk 800 + Switzer
  3. Panchang 800 for short display only + Switzer

**Shape and elevation:**
- Radius 0 on every element: buttons, inputs, tags, drawer, exhibits, dialogs.
- No drop shadows. Exhibits sit on a 1.5px ink border, with a mark slab offset behind them on a separate parallax layer.

**Icons and layers:**
- `@phosphor-icons/react`, set through `IconContext` to weight `bold`, size 20. No hand-drawn SVG icons.
- Z-index scale (`styles/layers.ts`): header 10, drawer 20, popover 30, dialog 40, toast 50.

**Copy rules** (checked with grep):
- Zero em/en dashes.
- One label per intent: "Enter demo", "See how it works", "New case", "Assess", "Answer", "Try a hypothetical", "Export report".
- No section-number eyebrows, scroll cues, version labels or decorative dots.
- The app header always shows "Demo corpus: fictional policies" (plan §2.2).
- A front-door section is only shipped if the feature it shows is implemented.

## Motion system

Every animation has a stated reason. All of it collapses to static under `prefers-reduced-motion`, and Lenis turns off.

| Moment | Where | Tech | Why it exists |
|---|---|---|---|
| Smooth scroll | Front door | `lenis/react` `<ReactLenis root options={{ lerp: 0.1 }}>`; anchors via `lenis.scrollTo`; touch stays native | Makes the sticky, parallax and 3D story read as one continuous motion |
| Policy stack | Hero | R3F canvas | Dramatizes retrieval: many policies narrow to one clause |
| Headline sweep | Hero, then reused in the app | Motion, `background-size` 0→100% with `box-decoration-break: clone`, 420ms, `[0.2,0.8,0.2,1]` | Names the thesis; in the app, marks the evidence span. Paint-only on a few spans; this exception is documented. |
| Parallax layers | Hero H1 (y 0→−80px); exhibit frames (±40px); mark slabs (1.3× speed) | Motion `useScroll` + `useTransform`. Lenis drives window scroll, so no extra wiring is needed. | Separates illustration depth from copy |
| Exhibit straighten | Section 2 | `rotateX` 14°→0 and scale 0.92→1 on entry | Hands off from the 3D hero to the real product |
| Tab auto-advance | Section 3 | Motion progress bar on the active tab, 6s; pauses on hover or focus | Shows which feature the exhibit is depicting |
| Scroll-scrubbed trace | Section 4 | `useScroll` progress feeds the real `RunTimeline` in replay mode | Tells the five-role story in order |
| Exhibit scripts | Every exhibit | `useExhibitScript(steps)`: plays once at 40% in view, has a Replay button, pauses offscreen | Shows the interaction itself (click finding → drawer → sweep) |
| Verdict reveal / stage track | App and exhibits | Motion, driven only by real run events | State transition and real progress |

No GSAP. Three.js lives in isolated canvas leaves, so Motion never animates inside a canvas. The canvas reads scroll progress from a mutable ref that Lenis's `useLenis` callback writes.

## Front door `/` (Notion-style product storytelling)

Eight sections, each a different layout family. At most two image-and-text splits in a row, zero eyebrows planned, no marquee, no scroll cue. `min-h-[100dvh]` hero, top padding at most `pt-24`.

1. **Hero with 3D policy stack.** Per FIRST VIEWPORT. The H1 is the LCP element, and the canvas loads after first paint.
2. **Full-bleed product shot:** exhibit E1 Workspace, the complete case workspace showing "Non-compliant.", its findings and the evidence drawer open on §4.2. It straightens in perspective as it enters, with a mark slab behind. One caption below it: "Sample case with fictional policies."
3. **Feature tabs** (the Notion "tabs + screenshot" pattern), headline "One case, from question to evidence." A tab list on the left swaps a framed exhibit on the right (crossfade with `layoutId`):
   - Ask a policy question → E2 Lookup (grounded answer with citations, F06)
   - Assess a scenario → E3 Assess (stage track runs, verdict reveals)
   - Open the evidence → E4 Evidence (policy detail; the sweep lands on the exact span)
   - Try a hypothetical → E5 Hypothetical (draggable before/after, labeled "Hypothetical")
4. **Sticky scrollytelling**, headline "Five specialists, one traceable answer."
   - The left column pins the stage names Retrieve, Analyze, Assess risk, Validate and Recommend, each with one plain line.
   - The right column pins E7 Trace, which advances with scroll.
   - The agent-message artifacts drift on parallax layers at different speeds.
5. **Split, text left:** "Unknown stays unknown." Exhibit E6 Clarification shows the question, its reason, "I don't know", and facts tagged provided / inferred / unknown.
6. **Split, exhibit left:** "Policies change. Old decisions stay reproducible." Exhibit E8 VersionDiff shows the v1→v2 retention clause added, with the snapshot pinned. This section ships only if F20 ships; otherwise it shows the version selector from P06.
7. **Bento**, headline "Built for review, not just answers." Exact cell counts:
   - 4 cells: E9 Review disposition, E10 Report export (real first page of the export), E11 Avatar (live if capable, otherwise poster), E12 Evaluation.
   - E12 renders only real numbers from `docs/evaluation/results.json`. Without it, the bento becomes 3 cells in a 1+2 layout.
8. **Close:** headline "Try the vendor case yourself.", the "Enter demo" button, then a footer with the fictional-corpus disclaimer and links to the repo, the architecture PDF and the evaluation report.

**Exhibit system** (`features/front-door/exhibits/`):
- Exhibits are the real app components (the plan §12.5 set) rendered with fixture scenes. They are not div mock-ups and not hand-drawn.
- `<Exhibit scene width={1280} height={800}>` renders at a fixed logical size and scales to fit its container using a ResizeObserver and `transform: scale`. This makes them behave like screenshots at every width.
- Each exhibit is a `<figure>` with `aria-label` and a figcaption. Its internals are `inert`, so keyboard and screen-reader users skip the illustrative controls.
- Static fallback: `scripts/capture-exhibits.ts` uses Playwright to capture each exhibit's final frame as AVIF/PNG. These captures serve reduced motion, screens under 768px (except E1 and the E5 slider), the OG image, and the README. The captures are real screenshots of real components.

**Three.js policy stack** (`features/front-door/PolicyStack.tsx`, lazy-loaded R3F):
- **Content:** 12 thin paper planes with rough `meshStandardMaterial`, carrying real fictional-corpus titles and clause lines via drei `<Text>`.
- **Lighting:** one soft key light plus ambient. No real-time shadows, no post-processing.
- **Idle:** slow drift, plus a damped tilt toward the pointer using `maath/easing` and `state.pointer`.
- **Scroll (hero progress 0→1):** the sheets fan out along z, the Data Sharing §4.2 sheet turns to face the camera and comes forward, and a mark-colored plane scales across the clause line. The canvas then fades as E1 rises.
- **Budgets:**
  - DPR `[1, 1.5]`.
  - `frameloop="never"` when offscreen, via IntersectionObserver.
  - The 3D chunk beyond three stays under about 60 KB gzipped.
- **Fallback:** a captured poster frame is used under reduced motion, when WebGL is unavailable, below 768px, or when `saveData` or `hardwareConcurrency ≤ 4`.

**Mobile:**
- Sections 3 and 4 collapse. Tabs become scroll-snap pills with no auto-advance, and the sticky story becomes stacked stage blocks, each with its static capture.
- Splits stack exhibit-first.
- The hero shows the poster frame under the H1.

**Imagery:** Phase 0 runs impeccable `context.mjs` to check for image generation.
- **If available:** produce the hero poster refinement, a macro photo of a highlighted printed policy page for section 5's slab, and the avatar's 2D fallback. Record provenance with `embed-prompt.mjs`.
- **If not:** use verified open-license photos or labeled slots, and put them on the replacement list at handoff.

## App `/app/*` (Operate mode; content as in plan §12, restyled)

**Shell:**
- 64px top bar: a Clash Display wordmark "Clause" with a mark underline, then Cases, Policies and Reviews.
- A "More" menu holds Reports, Evaluation and Settings.
- Also in the bar: the demo-corpus tag, a "Fixture data" tag while mocked, and "New case".
- Fits on one line at 1024px and up.

**P04 Case workspace (built first; source of the E1/E3/E5/E6 exhibits).**
- **Header:** title, scope, as-of date, snapshot ID, run state and "Export report".
- **Left 38%:**
  - Conversation.
  - Fact tags marked provided / inferred / unknown.
  - Inline clarification with "I don't know".
  - Composer that keeps unsent text if an error occurs.
  - 180px avatar.
- **Right 62%:**
  - `VerdictHeadline`. Copy per status:
    - "Non-compliant."
    - "Compliant within scope."
    - "Not enough to decide."
    - "Policies conflict."
    - "Outside the policy corpus."
  - A one-sentence summary.
  - Tabs: Assessment / Requirements / Trace.
  - Requirement matrix: requirement, result, facts and missing information, evidence (`§4.2 v1`).
  - Actions grouped by gap.
- **Evidence drawer:** clicking a finding opens it, and the clause sweeps. It shows version and effective date and links to "Open in policy".
- **Running state:** `StageTrack` driven by real events, with skeletons shaped like the finding rows.
- **States:** queued, per-stage, clarification, failed, canceled, reconnecting, and every assessment status.
- **F19:** "Try a hypothetical" shows a labeled before/after branch.
- **Responsive:** tablet uses Conversation / Assessment / Evidence tabs. Mobile shows a single pane with a bottom composer.

**Other pages:**
- **P06 Policy detail:** sticky outline, source text at 68ch with large tabular clause numerals in the margin, version selector, a `?clause=` deep link that scrolls and sweeps, pdf.js "View original page", inline extraction warnings.
- **P05 Policy library:** rows, filters, ingestion status, admin upload.
- **P03 Case index:** rows. The result is a colored word plus an icon, not a pill.
- **P02 Overview:** first viewport is a big "Describe what you're planning to do" composer. Below it: recent cases and corpus status.
- **As capacity allows:** P07 diff (strike in violated red, additions in the mark), P08 reviews, P09 evaluation (real numbers only, bars without background tracks), P10 reports, P11 settings (theme, motion, avatar). P12 is deferred.

**Avatar (F23, plan §11):**
- Stylized bust in matte paper-gray and ink, with one mark-colored detail, in a square panel.
- `AvatarController` is a pure state machine, unit-tested first, and reads the run-event store.
- R3F with `frameloop="demand"`, lazy-loaded, with a 2D fallback and a disable toggle.

## Architecture and dependencies (`apps/web`, plan §4.4 layout)

- **Stack:**
  - React 19, TypeScript (strict), React Router data router, TanStack Query.
  - Tailwind v4 via `@tailwindcss/vite`.
  - Motion, Lenis.
  - Radix headless primitives, Zustand, clsx.
  - three + R3F v9 + drei + maath, lazy-loaded.
  - pdfjs-dist, lazy-loaded.
- **API seam.** `lib/api/client.ts` defines a `ComplianceApi` interface with two implementations:
  - `FixtureApi`: plays the §5.3 fixture, the §10 vendor scenario and scripted SSE sequences.
  - `HttpApi`: plan §5.4 routes plus `EventSource`, using types generated in `packages/contracts`.
  - Switched with `VITE_API_MODE`.
- **Event store.** `lib/events/runStore.ts` deduplicates by `event_id` and reconciles by `sequence`. The UI, the stage track and the avatar all read from it.
- **Routes:**
  - `/`, `/sign-in`, `/app`
  - `/app/cases`, `/app/cases/new`, `/app/cases/:caseId`
  - `/app/policies`, `/app/policies/:policyId/versions/:versionId`
  - `/app/policy-changes/:changeId`, `/app/reviews`, `/app/evaluation`, `/app/reports`, `/app/settings`
- **Install commands:**

```
pnpm create vite apps/web --template react-ts
pnpm --dir apps/web add react-router @tanstack/react-query motion lenis @phosphor-icons/react zustand clsx @radix-ui/react-dialog @radix-ui/react-tabs @radix-ui/react-popover @radix-ui/react-dropdown-menu @radix-ui/react-tooltip three @react-three/fiber @react-three/drei maath pdfjs-dist
pnpm --dir apps/web add -D tailwindcss @tailwindcss/vite @types/three vitest jsdom @testing-library/react @testing-library/user-event @playwright/test @axe-core/playwright
```

Fonts: download the woff2 files for Clash Display, Switzer, and the two proof alternates from fontshare.com.

## Build sequence (fits plan §16 frontend lane)

- **Phase 0 (Day 1 AM):**
  - Run impeccable `context.mjs`, then `init` to write PRODUCT.md.
  - Scaffold the app and install dependencies.
  - Build tokens, `@font-face`, primitives, `FixtureApi`, the event store and the fixtures.
  - Run the **font proof** and get the user's confirmation.
  - If image generation exists, produce comps for the hero and P04 (comp-led).
- **Phase 1 (Day 1–2):** P04 against fixtures, covering all states, the sweep, the drawer and the responsive layouts.
- **Phase 2 (Day 2):** shell, P06 and P05 with citation deep links, P03, P02, `/sign-in`.
- **Phase 3 (Day 3):** front door. Covers the exhibit system and scripts, Lenis, parallax, the feature tabs, the sticky trace, the 3D policy stack with its poster fallback, and exhibit captures.
- **Phase 4 (Day 3–4):** `HttpApi` and SSE reconnect as the backend lands, F22 Trace, F19 hypothetical, F23 avatar.
- **Phase 5 (Day 4–5):**
  - P07–P11 as capacity allows, and cut any front-door section whose feature didn't ship.
  - Dark theme verification.
  - Accessibility, responsive and performance sweep.
  - Impeccable finish review and documenter, which writes DESIGN.md.
  - Update `IMPLEMENTATION_PLAN.md` §12.1–12.8 (direction, routes, tokens, fonts, tracker) to match.

## Verification

- **Manual flow:** `pnpm --dir apps/web dev`, then `/` → scroll the whole story → "Enter demo" → vendor case → answer clarification → verdict → open finding (sweep on §4.2) → "Try a hypothetical" → export.
- **Automated checks:** `pnpm --dir apps/web lint`, `typecheck` and `test`.
  - Vitest covers `AvatarController`, run-store dedup/reorder, status copy, and the `useExhibitScript` timeline.
  - Playwright covers:
    - the main flow and SSE reconnect
    - reduced motion (Lenis off, posters shown, no transforms)
    - no-WebGL fallback
    - `@axe-core/playwright` on every route
- **Screenshots:** 1440×900 and 390×844, light and dark, saved to `.impeccable/review/`. Then run `detect.mjs --json` once, the finish reviewer (at most two rounds), and the documenter.
- **Taste pre-flight, run mechanically:**
  - `grep -rnP "[\x{2013}\x{2014}]" apps/web/src` returns nothing.
  - Hero H1 is at most 2 lines at 1440 and the CTAs are visible without scrolling.
  - No more than 2 consecutive splits.
  - Bento cell count matches its content.
  - One label per CTA intent.
  - Radius-0 audit.
  - The mark is never used as text, border or focus color.
  - Every exhibit is backed by a shipped feature.
- **Performance:**
  - Lighthouse on `/` and `/app/cases/:id`: LCP < 2.5s, CLS < 0.1, INP < 200ms.
  - The 3D chunk loads after LCP.
  - A stable 60fps scroll on the front door at 1440 is observed in the Performance panel.
