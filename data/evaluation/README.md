# Evaluation scenarios (answer keys)

Hand-labelled scenarios for F14. **Never indexed**: ingestion and retrieval read only `data/demo/`. Do not paste these labels, rationales or expected outputs into prompts.

## Splits

| Split | File | Status | Use |
|---|---|---|---|
| Development | `dev/scenarios.json` | 13, reviewed against clause text 2026-09-26 | Tuning prompts, retrieval and thresholds |
| Held-out test | `test/scenarios.json` | 20 authored 2026-09-26, awaiting the project owner's review; not yet run | Final measured results only; never used for tuning |

Keep paraphrases and counterfactual variants of one scenario family in the same split (the `family` field). The held-out set is best written or reviewed by someone who is not tuning the system; model agreement alone is not ground truth.

The CLI validates the selection before database setup. Disputed records are excluded before `--limit` is applied; zero/negative limits are rejected. Every eligible test record must be marked `reviewed`, even for a limited run. The owner must still freeze the file manually before the final run: the review-status check is not proof of independent review or an immutable freeze. New reports record SHA-256 hashes of the full scenario file and corpus manifest, count reviewed labels only within the evaluated sample, and retain a unique raw JSON file for each run. Failed runs remain in accuracy and requirement-label denominators. These safeguards were tested on temporary synthetic inputs; the real held-out split remains unrun.

## Record fields

- `id`, `split`, `family`, `category` (plan §13.1), `tags`
- `scenario`: the requester's words; `as_of`: the date the activity takes place (selects policy versions)
- `facts`: what the scenario establishes, each `provided`, `inferred` or `unknown`
- `requirements`: expected requirement labels keyed by clause ID (`met`, `violated`, `unknown`, `not_applicable`, `conflict`)
- `evidence_sets`: acceptable sets of clause IDs that support the decisive findings; any one set is enough
- `expected_missing_facts`, `acceptable_status` (one or more assessment statuses), `recommendation_clauses`
- `notes`: why the label is what it is, with the clause text that decides it
- `review`: `authored` → `reviewed` → `disputed` (disputed labels are excluded from definitive claims)

`services/api/tests/test_evaluation_labels.py` checks both files on every test run: every named clause exists, belongs to a published version in force on `as_of`, expected missing facts are marked unknown, and no family appears in both splits.

## Held-out split coverage

| Category | Scenarios | Expected results |
|---|---|---|
| Explicit violations and thresholds | test-001, 002, 004, 013, 016, 020 | 3 non-compliant, 3 compliant (boundary and conversion traps) |
| Missing material facts | test-003, 006, 014 | insufficient information |
| Exceptions and conditional requirements | test-005, 007, 011, 015 | 3 compliant through an exception, 1 non-compliant (a litigation hold overrides) |
| Conflicts and version changes | test-008, 012 | non-compliant: a draft version that is not in force; an expired vendor review under Data Sharing v2 |
| Multiple policies | test-010, 018 | non-compliant: past sharing plus reporting duties; an invalid policy exception |
| Adversarial or misleading | test-009 | non-compliant: an affiliate framed as "internal" |
| Single policy | test-017 | non-compliant |
| Out of corpus | test-019 | out of scope |

Totals: 10 non-compliant, 6 compliant within scope, 3 insufficient information, 1 out of scope. No held-out case expects `conflicting_policy`: the corpus has one genuine two-policy conflict (claim-record retention against model-training retention) and it belongs to the dev family `training-data-retention`. Reusing it would leak a tuned case into the test split.

## Review log

**Dev split, 26 September 2026.** Every label was re-read against the clause text by the Claude Code assistant, not by an independent person. Changes:

- dev-004: the claim was submitted on 2 April 2026, after Expense Approval v2 took effect, so the approval could reasonably be judged under v2. The submission date is now 27 March, which keeps the whole claim under v1.
- dev-009: Governance §4.1 changed from `met` to `unknown`; nothing in the scenario says the conflict was escalated to the Policy Committee. Added the unknown fact `policy_committee_decision`.
- dev-011: added "starting today", so the plan clearly grants access before the confidentiality agreement is on file.
- dev-013: "about 14 hours later" was measured from the theft, but Incident Response §3.1 runs from noticing. The scenario now says the theft was noticed yesterday evening.
- dev-008: added a note that a regulator is not a vendor, so Vendor Due Diligence is not labelled.

**Held-out split, 26 September 2026.** Twenty scenarios authored by the same assistant that built the system, so they are marked `authored`. Before the final run, the project owner should read each `notes` field against the policy, mark agreed labels `reviewed` (or `disputed`), and then freeze the file. The split has not been run, not even for retrieval, so no system output has influenced these labels.
