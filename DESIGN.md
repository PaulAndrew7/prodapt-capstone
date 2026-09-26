---
name: Clause
description: Every verdict, pinned to its clause. A policy-compliance workspace where each finding points to the exact words that justify it.
colors:
  paper: "#f4f6f5"
  sheet: "#fbfcfb"
  ink: "#111413"
  ink-2: "#4a524e"
  rule: "#d5dad7"
  mark: "#ddff3c"
  on-mark: "#111413"
  violated: "#b42318"
  unknown: "#8a5a00"
  met: "#1d6b45"
  muted: "#6b726e"
  paper-dark: "#0e1110"
  sheet-dark: "#151918"
  ink-dark: "#edf1ee"
  ink-2-dark: "#a3ada8"
  rule-dark: "#2a302d"
  violated-dark: "#ff8a7a"
  unknown-dark: "#f2b84b"
  met-dark: "#6fd39b"
  muted-dark: "#8a938e"
typography:
  display:
    fontFamily: "Clash Display, Switzer, ui-sans-serif, sans-serif"
    fontSize: "clamp(3rem, 6.4vw, 6rem)"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.012em"
  verdict:
    fontFamily: "Clash Display, Switzer, ui-sans-serif, sans-serif"
    fontSize: "clamp(2.75rem, 4.8vw, 5.25rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Clash Display, Switzer, ui-sans-serif, sans-serif"
    fontSize: "clamp(2.25rem, 4.6vw, 4.5rem)"
    fontWeight: 700
    lineHeight: 1.03
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Clash Display, Switzer, ui-sans-serif, sans-serif"
    fontSize: "clamp(1.75rem, 2.6vw, 2.5rem)"
    fontWeight: 600
    lineHeight: 1.1
  clause-number:
    fontFamily: "Clash Display, Switzer, ui-sans-serif, sans-serif"
    fontSize: "3.75rem"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "\"tnum\""
  lead:
    fontFamily: "Switzer, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1.625
  clause-text:
    fontFamily: "Switzer, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.7
  body:
    fontFamily: "Switzer, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Switzer, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.43
  tag:
    fontFamily: "Switzer, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1
rounded:
  none: "0px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  gutter: "16px"
  gutter-md: "32px"
  section: "112px"
  section-md: "160px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 20px"
    height: "44px"
  button-mark:
    backgroundColor: "{colors.mark}"
    textColor: "{colors.on-mark}"
    rounded: "{rounded.none}"
    padding: "0 20px"
    height: "44px"
  button-mark-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 20px"
    height: "44px"
  button-outline-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  button-lg:
    padding: "0 28px"
    height: "56px"
  button-sm:
    padding: "0 12px"
    height: "36px"
  input-field:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 12px"
    height: "48px"
  menu-item-highlighted:
    backgroundColor: "{colors.mark}"
    textColor: "{colors.on-mark}"
    padding: "0 16px"
    height: "40px"
  tag-origin:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.tag}"
    rounded: "{rounded.none}"
    padding: "0 6px"
    height: "24px"
  app-header:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-2}"
    height: "64px"
  drawer-evidence:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    width: "min(640px, 92%)"
---

# Design System: Clause

## Overview

**Creative North Star: "The Highlighter"**

Clause is a stack of cool paper worked over with one fluorescent pen. Everything the user reads is ink on paper or sheet, ruled with heavy 2px ink lines, square at every corner, with nothing floating above anything else. The single highlighter colour does one job: it sits behind ink to say "these are the words that matter". A verdict is set large in Clash Display; the clause behind it is set in readable Switzer with the cited words swept in mark.

The system is dense where the work is (the case workspace is a 38/62 split of conversation and assessment, ruled into panes) and generous where the story is told (the front door runs 112 to 160px section rhythm around large display headlines and scaled product exhibits). Depth is never shadow; on the front door it comes from parallax layers and a Three.js stack of policy sheets, and inside the app it does not exist at all beyond drawers sliding over ruled panes.

The build refuses two worlds by name: the dark AI dashboard with a score dial, and the cream editorial serif workspace. The palette is cool and neutral, the type is grotesque, and no status is ever a percentage or a gauge.

**Key Characteristics:**
- Cool paper and sheet surfaces with near-black ink; one fluorescent mark used only as a fill behind ink.
- 2px ink rules as the structural line; 0px radius everywhere; no drop shadows.
- Clash Display for headlines, verdicts and clause numbers; Switzer for all working UI.
- The highlighter sweep is the signature motion, and it only ever marks exact stored quote text.
- Status is always a word plus a bold Phosphor icon, never colour alone.
- Light theme is primary; dark follows the system or a pinned `data-theme`.

## Colors

A near-monochrome cool neutral ground with one fluorescent accent and three quiet semantic tones.

### Primary
- **Highlighter Lime** (`mark`): the one accent. Used as a fill behind ink only: the highlighted clause span, the Enter demo button, the active nav underbar (4px), the highlighted menu row, the active stage in the stage track, hover fill on evidence links, text selection, the wordmark bar, and the parallax band behind the front-door product shot. Identical in both themes.
- **On-Mark Ink** (`on-mark`): the only colour text may take on the mark, in both themes, including dark mode where regular ink turns light.

### Neutral
- **Cool Paper** (`paper` / `paper-dark`): the page ground, header background and inset field background.
- **Sheet White** (`sheet` / `sheet-dark`): raised working surfaces: drawers, menus, inputs, error notices. Differs from paper by tone, never by shadow.
- **Graphite Ink** (`ink` / `ink-dark`): all primary text, 2px rules, borders, focus outlines, primary button fill.
- **Slate Ink** (`ink-2` / `ink-2-dark`): secondary text, leads, metadata, inactive nav, placeholders, scrollbar thumb.
- **Hairline Grey** (`rule` / `rule-dark`): light dividers between table rows, the empty stage track, skeleton fill (at 70%).
- **Muted Grey** (`muted` / `muted-dark`): the out-of-scope and not-applicable status tone and skipped stages.

### Semantic
- **Violated Red** (`violated`): non-compliant status word and icon; error notice border.
- **Unknown Amber** (`unknown`): not-enough-information status and unknown fact tags.
- **Met Green** (`met`): compliant and met status.
- Conflict uses plain ink with the scales icon, not a fourth hue.

### Named Rules
**The Fill-Only Rule.** The mark is never a text colour, border colour, outline or focus colour; it fails 3:1 on paper. It appears only as a fill with on-mark ink on top of it.

**The One Pen Rule.** There is one highlighter. No second accent, no gradients of it, no tints of it as a background wash. Rarity is what makes a marked span read as evidence.

**The Word-and-Icon Rule.** Every status is a label plus a bold Phosphor icon in the status tone. Colour alone never carries meaning, and no status is ever expressed as a score, percentage or dial.

## Typography

**Display Font:** Clash Display 600/700, self-hosted (with Switzer, ui-sans-serif fallback)
**Body Font:** Switzer variable 100 to 900, self-hosted (with ui-sans-serif, system-ui fallback)

**Character:** Clash Display is compressed and assertive, so a verdict reads like a stamp; Switzer is plain and even, so long clause text and dense workspace UI stay calm. Clash Display's word space is opened slightly (0.045em) wherever it is used.

### Hierarchy
- **Display** (700, clamp 3 to 6rem, 1.02, -0.012em): the front-door hero headline only, max about 15ch.
- **Verdict** (700, clamp 2.75 to 5.25rem, 1.05, -0.01em; md and xl variants from 2.25 to 6rem): the assessment result, sentence case with a full stop ("Non-compliant."). Words rise out of a line mask on arrival.
- **Headline** (700, clamp 2.25 to 4.5rem, 1.03, -0.01em): front-door section headings, max about 17ch.
- **Title** (600, clamp 1.75 to 2.5rem, 1.1): workspace and page titles in the app, max about 28ch. Empty-state titles use Clash Display 700 at 1.875rem.
- **Clause Number** (700, 3.75rem, 1, tabular): the section number that heads each cited clause in the evidence drawer.
- **Lead** (400, 1.125 to 1.375rem, relaxed, ink-2): subtext under display and section headlines, 40 to 50ch.
- **Clause Text** (400, 1.125rem, 1.7): the reading size for policy clauses carrying the mark, max 62ch.
- **Body** (400, 1rem, 1.55): default UI text; prose held to 52 to 64ch.
- **Label** (600, 0.875rem): nav items, button text, table headers, metadata, captions. Sentence case.
- **Tag** (600, 0.75rem): origin tags and header badges only.

### Named Rules
**The Two Faces Rule.** Clash Display is for headlines, verdicts, clause numbers and the wordmark; everything a user operates is Switzer. Never set a control, label or paragraph in Clash Display.

**The Sentence Case Rule.** No uppercase tracked labels anywhere. Headings, labels and verdicts are sentence case; verdicts end with a full stop.

**The Tabular Evidence Rule.** Clause numbers, page numbers, dates, version labels and request IDs use tabular figures.

## Layout

Two containers: the front door centres at 1400px, the app at 1600px, both with 16px gutters rising to 32px at 768px. The app header is a 64px ruled bar; the front-door header is 72px.

From 1024px up, the case workspace is a full-height split: conversation and facts in a 38fr column, assessment in a 62fr column, separated by a 2px ink rule, each pane scrolling independently. Below 1024px the panes become a ruled tab strip and show one at a time. The evidence drawer slides over the assessment pane from the right at min(640px, 92%) and goes full width on mobile.

Spacing follows a 4px base used at 4, 8, 16, 24, 40px steps inside components; front-door sections breathe at 112px, 160px from 768px. Prose measures are capped in ch (40 to 64ch) rather than by column width. Lists of cases and policies are ruled tables that collapse to stacked rows on mobile.

Lenis smooth scroll, parallax and WebGL run on the front door only; the app keeps native scroll.

## Elevation & Depth

There are no shadows in this system. Surfaces separate by tone (paper versus sheet) and by 2px ink rules. Overlays (drawers, menus) sit on sheet with a 2px ink border and no shadow or scrim glow.

On the front door, depth is literal and spatial rather than material: a Three.js stack of unlit policy sheets bleeds off the right edge of the hero and brings clause 4.2 forward on scroll; product exhibits tilt in with perspective; a mark band drifts behind the product shot at a different scroll rate. The 3D scenes use unlit (basic) materials with ink outlines, so even the WebGL layer carries no shading or cast shadow. Where WebGL is unavailable, on small screens, low-power devices, save-data or reduced motion, a raster captured from the project's own scene stands in, with provenance recorded in a JSON sidecar.

### Named Rules
**The Flat Paper Rule.** No `box-shadow`, no `drop-shadow`, no blurred glow, anywhere. If something needs to feel above, give it sheet, a 2px ink border, or a place in the parallax.

**The Front Door Only Rule.** Parallax, smooth scroll and 3D belong to the front door. The working app never moves the page for effect.

## Shapes

Every corner is square (0px). Structural lines are 2px ink: header bottoms, pane dividers, table heads, inputs, outline buttons, drawers, menus. Lighter dividers between rows are 1px hairline grey. Scaled miniatures (product exhibits) and small tags use a 1.5px ink line so they read at reduced scale. Dashed ink borders mean "inferred" or "fixture": dashed is a data-provenance signal, not decoration.

The highlighter is a shape too: a flat fill 88% of the line height, sitting slightly below centre (background-position 58%), with 0.08em horizontal overhang, cloned per line so a wrapped span is marked line by line.

## Components

### Buttons
Blunt, square and heavy; a pressed button drops 1px.
- **Shape:** square corners (0px).
- **Primary:** ink fill, paper text, Switzer 600. Sizes: 36px (sm, 12px padding), 44px (md, 20px), 56px (lg, 28px), 48px square icon.
- **Mark:** mark fill with on-mark text; reserved for the one entry action (Enter demo). Hover inverts to ink fill with paper text.
- **Outline:** 2px ink border, ink text; hover fills ink.
- **Ghost:** ink text, underline on hover.
- **Hover / Focus:** 150ms colour transition on the shared ease-out; focus is a 2px ink outline at 2px offset; active translates 1px down; disabled at 45% opacity.
- **Loading:** a small pulsing square in currentColor replaces the icon.

### Chips / Tags
- **Style:** 24px tall, 1.5px border, 0.75rem semibold, no fill.
- **State:** provided is solid ink; inferred is dashed ink (with ", unconfirmed" appended until confirmed); unknown is amber border and text with a question icon.

### Cards / Containers
- **Corner Style:** square (0px).
- **Background:** paper for ground, sheet for anything that sits on it.
- **Shadow Strategy:** none; see Elevation & Depth.
- **Border:** 2px ink for containers that must read as separate; ruled sections (top or bottom 2px ink) are preferred over boxed cards.
- **Internal Padding:** 20 to 24px in notices and drawer heads; 32 to 40px in workspace panes.

### Inputs / Fields
- **Style:** 48px tall single-line, sheet fill, 2px ink border, square, 12px horizontal padding; the scenario composer is a larger 1.125rem textarea with 16px padding.
- **Focus:** 2px ink outline at 2px offset.
- **Error / Disabled:** errors surface in a notice with a 2px violated border on sheet and a warning icon; disabled fields drop to 50% opacity.

### Navigation
- **App header:** 64px, paper, 2px ink bottom rule, sticky. Items are Switzer 600 in ink-2, ink on hover; the active item is ink with a 4px mark underbar inset 12px from each side.
- **Menus:** sheet panel with 2px ink border; rows 40px, highlighted row fills mark with on-mark text.
- **Mobile:** below 1024px the nav collapses into a 40px square outlined menu button opening the same menu.
- **Skip link:** mark fill with on-mark text when focused.

### Highlighter Mark (signature)
The span that pins a verdict to its words. Animates a `--sweep` custom property from 0% to 100% of the background width (420ms default, ease-out), so wrapped text sweeps line by line. It marks a span only when the stored quote is an exact substring of the clause text; otherwise the clause renders unmarked. Instant under reduced motion. Evidence links that open a clause take the same fill on hover.

### Verdict Headline
The assessment result set in Clash Display, each word rising out of an overflow mask with a 80ms stagger, paired with a word-and-icon status line. No score, no dial.

### Stage Track
Five equal 6px bars for the five review roles, driven only by real run events: hairline grey when pending, ink when done (scaling in from the left), a moving mark segment while active, struck-through muted label when skipped.

### Evidence Drawer
Sheet panel with a 2px ink left rule sliding in over 280ms. Per citation: policy title, version and page in tabular ink-2, the clause number in Clash Display, the clause text at reading size with the quote swept in mark, and an "Open in policy" link.

### Exhibit
On the front door, product explanations are real app components rendered at a fixed logical size (1280 by 800 by default), scaled to fit, framed in a 1.5px ink border on paper, and made inert and hidden from assistive tech; the figure label describes them. Exhibits step through states while 40% in view, pause offscreen, show the final state under reduced motion, and offer a Replay link.

### Avatar
An unlit sheet-white figure with an ink inverted-hull outline and a mark collar; features are ink, turning muted grey when unavailable. It is optional: every task works without it.

## Do's and Don'ts

### Do:
- **Do** put on-mark ink (#111413) on every mark fill, in both themes.
- **Do** separate surfaces with paper versus sheet and 2px ink rules.
- **Do** pair every status with its word and a bold Phosphor icon.
- **Do** mark only exact stored quote substrings; render the clause unmarked if the quote does not match.
- **Do** use function-form `useTransform` for scroll-linked opacity so Motion does not hand it to a mismatched native ViewTimeline.
- **Do** collapse all motion under `prefers-reduced-motion`: sweeps land instantly, exhibits show their final state, 3D and parallax are replaced by static rasters.
- **Do** capture fallback rasters from the project's own 3D scenes and keep their provenance next to them.
- **Do** open Clash Display word spacing (0.045em) wherever it is set.

### Don't:
- **Don't** use the mark as text, border, outline or focus colour.
- **Don't** round a corner or add a shadow, glow or blur to lift a surface.
- **Don't** show status as a score, percentage, gauge or dial, or by colour alone.
- **Don't** build a dark AI dashboard or a cream editorial serif workspace.
- **Don't** set controls, labels or body copy in Clash Display.
- **Don't** add uppercase tracked kickers or eyebrows above headings.
- **Don't** bring Lenis, parallax or WebGL into the app; it keeps native scroll.
- **Don't** fake an exhibit with a screenshot or mock markup when the real component can be rendered.
