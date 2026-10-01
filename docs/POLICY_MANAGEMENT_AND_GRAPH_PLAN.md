# Policy management and knowledge graph

> **Update, 1 October 2026:** the graph page, the `/api/v1/policy-graph` endpoint and its schemas were removed. Stored clause relations remain and retrieval still uses them. The Graph section below is kept as the original plan.

Implementation scope agreed 30 September 2026: digital PDF upload/replacement, extraction preview, editable draft metadata and clause classifications, reviewed relationships, publication, dated graph navigation and a version comparison. Published source text is immutable. Editing policy content means uploading a replacement PDF as a new version; an in-browser document authoring system is outside this batch.

## Workflow

1. An organization admin uploads a digital PDF for a new policy or an existing policy. Validate file limits, dates, labels and organization access. Use the existing parser, source storage and indexer. Ingest synchronously into a draft; show real pending/error state. No model is required. Scanned/encrypted/corrupt PDFs retain the existing explicit errors.
2. Preview every extracted clause and original page, including extraction warnings. Admins review clause kinds and which general clauses impose obligations. Save the reviewed candidate metadata on the version, rather than adding new hardcoded demo IDs to the workflow. Seeded/legacy demo metadata retains its documented classifications.
3. Preview extracted clause relationships. Admins can accept/reject them or add explicit links to another own-organization published clause. Record provenance, reviewer and review time. Newly managed policies use approved links in retrieval; proposed links do not establish exception/override semantics.
4. Edit draft label/effective dates and save a complete clause review. Publishing requires ready indexes, reviewed clauses and acknowledged extraction warnings. Lock the organization/version during publish, reject ambiguous start dates, save audit records and create a fresh immutable snapshot atomically. Repeated publication returns the original publication result.
5. Choose the newest eligible version per policy within the selected snapshot and assessment date. Do not modify the source, dates or classifications of earlier published versions. New assessments/search use the latest snapshot; waiting runs keep their original snapshot. Expired latest versions do not silently reactivate an older open-ended version.
6. Compare versions by logical clause section: added, removed and changed text/kind, with original sources. This is a textual comparison, not an automatic semantic policy ruling.

## Graph

Expose a read-only graph of policies, eligible versions, clauses and stored references/exceptions/overrides. Focus on one policy and its directly linked clauses; bound node counts and disclose truncation. Filter both endpoints by organization, snapshot and effective date. Draft links are managed in the review screen, not the published graph. Display relationship approval/provenance and exact sources; source existence does not prove the interpretation.

The graph has keyboard-operable nodes, policy/date filters, a source detail panel and an accessible relationship list. The SVG uses the existing design system and no separate graph database/service. A case graph can use the completed run's pinned snapshot/date and show finding-to-clause links; it must not infer dependencies absent from stored evidence. Retrieval continues to use the same stored graph with bounded expansion.

## API and UI

- Add admin upload, draft-review and publish endpoints plus read-only comparison and graph endpoints.
- Mirror contracts in the TypeScript API seam and regenerate OpenAPI.
- Add **Manage policies** and **Knowledge graph** navigation from the policy library, review/publish routes and version comparison. Fixture mode is labelled and cannot pretend to publish real documents.
- Preserve published source offsets. Display unpublished/draft status accurately in the library. Source links and existing case reports continue to resolve.

## Acceptance

- Upload → preview → review → publish → search/offline assessment uses the new clause and exact original source.
- Drafts never enter assessment evidence; requester cannot read drafts or perform admin writes.
- Invalid/oversized/scanned PDFs, duplicate labels, foreign IDs, stale/published edits and incomplete review fail without partial database publication.
- Publication is idempotent; organization locking serializes concurrent snapshot changes.
- Both versions at a date boundary behave correctly; old snapshots and saved results remain stable.
- Approved cross-policy links expand evidence only when both endpoints are eligible. Rejected/proposed links from managed uploads are excluded from interpretation.
- Graph contains only authorized, dated nodes; each edge resolves to visible endpoints; source links, keyboard/mobile navigation, comparison and reload work.
- Run backend/database regressions, contract/OpenAPI, lint/types, frontend tests/build, focused browser checks and a real no-model HTTP/browser smoke in a separate database. Preserve existing evaluation reports and held-out labels.

No Kafka, Neo4j service, semantic conflict detector, OCR, arbitrary PDF text editing or model retraining is needed for this scope.
