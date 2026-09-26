# Evaluation scenarios (answer keys)

Hand-labelled scenarios for F14. **Never indexed**: ingestion and retrieval read only `data/demo/`. Do not paste these labels, rationales or expected outputs into prompts.

## Splits

| Split | File | Status | Use |
|---|---|---|---|
| Development | `dev/scenarios.json` | 13 authored 2026-09-26, pending second review | Tuning prompts, retrieval and thresholds |
| Held-out test | `test/scenarios.json` | Not authored yet (target 20) | Final measured results only; never used for tuning |

Keep paraphrases and counterfactual variants of one scenario family in the same split (the `family` field). The held-out set is best written or reviewed by someone who is not tuning the system; model agreement alone is not ground truth.

## Record fields

- `id`, `split`, `family`, `category` (plan §13.1), `tags`
- `scenario`: the requester's words; `as_of`: the date the activity takes place (selects policy versions)
- `facts`: what the scenario establishes, each `provided`, `inferred` or `unknown`
- `requirements`: expected requirement labels keyed by clause ID (`met`, `violated`, `unknown`, `not_applicable`, `conflict`)
- `evidence_sets`: acceptable sets of clause IDs that support the decisive findings; any one set is enough
- `expected_missing_facts`, `acceptable_status` (one or more assessment statuses), `recommendation_clauses`
- `notes`: why the label is what it is, with the clause text that decides it
- `review`: `authored` → `reviewed` → `disputed` (disputed labels are excluded from definitive claims)
