# Corpus decision

Status: open question with the assessor; synthetic corpus in use  
Recorded: 2026-09-26 (F01)

## The mismatch

The project brief (page 3) describes the input as policy and compliance documents, but its dataset links point to PubMed, PubMed abstracts, PMC and BioNLP. Those are bibliographic records and scholarly biomedical articles, not an organization's internal policies. They contain no obligations, approvals, thresholds or exceptions to assess a business activity against. This looks like an inconsistency in the brief. That is our inference; the assessor has not confirmed it.

**Pending:** ask the assessor which documents are intended. Record the reply here with its date.

## What we use meanwhile

A synthetic policy corpus for **Kestrel Mutual**, an invented insurer. Every document says on its cover and in its running header that it is fictional and is not real policy, law or regulatory guidance. The app labels the corpus "Demo corpus: fictional policies". We do not claim that this corpus is the dataset the brief supplied.

Biomedical data stays out of the policy index unless the assessor changes the project domain and supplies matching policy requirements.

## Provenance rules

- Authored source text lives in `data/demo/policies/<version_id>.md`. PDFs in `data/demo/pdf/` are generated from it by `scripts/build_demo_corpus.py` and are byte-for-byte reproducible.
- `data/demo/manifest.json` records, per version: policy metadata, effective dates, status, SHA-256 of the source and of the PDF, page count, and provenance (`kind: synthetic`, author, license, allowed use). Seeding refuses a PDF whose hash does not match the manifest.
- Real policies are ingested only with written permission to process them, and with origin, version, effective date and allowed use recorded in the same provenance fields (`kind: provided`).
- Evaluation answer keys live in `data/evaluation/` and are never read by ingestion or retrieval. The seed command reads only `data/demo/`.

## Corpus design

11 policies, 14 versions, 111 clauses (counts from the manifest). Properties built in on purpose:

| Property | Where |
|---|---|
| Two versions with a date boundary | Customer Data Sharing v1 (to 30 Sep 2026) and v2 (from 1 Oct 2026, adds §4.5 retention period) |
| Threshold change across versions | Expense Approval v1 (line manager up to £1,000; superseded 31 Mar 2026) and v2 (up to £500, adds §3.3) |
| Draft version, never in a published snapshot | Change Management v2 (effective 1 Nov 2026, draft) |
| Explicit exceptions that replace a clause | Data Sharing §4.4 (legal disclosure, instead of §4.2), Vendor §3.4 (conditional approval, instead of §3.1), Change Management §3.1 (emergency change, instead of §2.2), Onboarding §4.1 (existing customers, under §2.1) |
| Unresolved conflict | Retention §5.1–5.2 (claim records and derived datasets deleted 7 years after closure) against Model Development §2.2 (training datasets kept for model life plus 3 years). Neither states precedence; Governance §4.1 requires escalation. |
| Definitions | Data Sharing §4.1, Retention §2.1, Incident Response §2.1–2.2 |
| Cross-references | Data Sharing §5.2 → §4.2, Access Control §2.3 → §3.1, and cross-policy mentions (Data Sharing §2.2 → Access Control Policy) |
| Deliberately irrelevant policy for the worked scenario | Remote Working |
| Numeric and date boundaries | Access Control §2.4 (14 days), Incident Response §3.1 (one hour), Onboarding §3.1 (£50,000), Expense §2.1–2.3 |

Clause text for the clauses the web fixtures use (Data Sharing §4.1–4.4, §5.1, Vendor §1, §3.1–3.3, Access Control §2.1, §2.4–2.5, Retention §5.1, §5.3, Model Development §2.2) matches `apps/web/src/fixtures/policies.ts` word for word, so fixture and live citations agree.
