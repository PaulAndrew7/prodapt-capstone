# Feature task records

> Scope update, 26 September 2026: the revised [implementation plan](../../IMPLEMENTATION_PLAN.md), especially sections 3, 7 and 8, governs the capstone submission. The individual records below retain the earlier roadmap's checklists and evidence. Update a task's checklist to the reduced scope before implementing it; deferred work must not be marked completed. Records rewritten on 26 September (F02, F05–F14, F16–F18, F22, F23) count items of the reduced-scope checklist; the rest still show historical counts. IN_REVIEW means implemented and tested with a scripted model, waiting for a real-model run.

One file per original feature package, generated 2026-09-26. Each record carries its own implementation evidence.

The [30 September offline batch](SESSION_2026-09-30_OFFLINE.md) implements model-independent assessments and source lookup, automatic failure fallback, cumulative user-confirmation batches, early completion and visible report provenance. No model provider was called for its verification; existing model evaluation results remain separate.

The [30 September coverage batch](SESSION_2026-09-30_COVERAGE.md) adds retrieved-candidate accounting, the evidence inspector, print/export coverage and broader evaluation metrics. Verification: 235 backend tests, 36 frontend unit tests and 24 browser tests passed. The latest Claude Sonnet 5.5 development run returned 12/13 correct final statuses; held-out and manual evidence-support review remain pending.

Latest: the [27 September input/progress batch](SESSION_2026-09-27.md) completed ten fixes. Verification totals: 178 backend tests and 26 frontend tests passed; production build passed. Required model/owner-review work remains pending.

The [26 September readiness batch](SESSION_2026-09-26.md) completed ten bounded acceptance tasks across F03, F04 and F15. Those three records now use the revised submission scope; deferred requirements remain explicitly excluded.

The [second readiness batch](SESSION_2026-09-26_B.md) completed twenty fixes across provider budgets/configuration, evaluation integrity and evidence/input UI. Backend tests: 164 passed; frontend tests: 18 passed. Model-dependent feature statuses remain unchanged.

| ID | Feature | Status | Progress |
|---|---|---|---|
| [F00](F00.md) | Repository, contracts, CI skeleton | IN_REVIEW | 5/5 |
| [F01](F01.md) | Corpus and scenario specification | IN_PROGRESS | 4/5 |
| [F02](F02.md) | Schema and versioned persistence | DONE | 5/5 |
| [F03](F03.md) | PDF ingestion and indexing | DONE | 5/5 |
| [F04](F04.md) | Policy library and source viewer | DONE | 5/5 |
| [F05](F05.md) | Hybrid retrieval | IN_PROGRESS | 4/5 |
| [F06](F06.md) | Grounded policy lookup | IN_REVIEW | 4/5 |
| [F07](F07.md) | Graph, A2A exchanges and handoffs | DONE | 6/6 |
| [F08](F08.md) | Compliance analysis and clarification | IN_REVIEW | 4/5 |
| [F09](F09.md) | Risk and gap assessment | IN_REVIEW | 4/5 |
| [F10](F10.md) | Interpretation and validation | IN_REVIEW | 4/5 |
| [F11](F11.md) | Remediation recommendations | IN_REVIEW | 4/5 |
| [F12](F12.md) | Case workspace and conversation | IN_REVIEW | 4/5 |
| [F13](F13.md) | Assessment and evidence UI | IN_REVIEW | 4/5 |
| [F14](F14.md) | Evaluation harness and report | IN_PROGRESS | 2/5 |
| [F15](F15.md) | Local demo safeguards and access checks | DONE | 5/5 |
| [F16](F16.md) | Reports and audit history | DONE | 3/3 |
| [F17](F17.md) | Deployment and recovery | IN_PROGRESS | 3/4 |
| [F18](F18.md) | Documentation and panel demo | IN_PROGRESS | 4/6 |
| [F19](F19.md) | Counterfactual scenario comparison | TODO | 0/5 |
| [F20](F20.md) | Policy changes and affected cases | TODO | 0/5 |
| [F21](F21.md) | Human review workflow | TODO | 0/5 |
| [F22](F22.md) | Execution timeline and replay | DONE | 2/2 |
| [F23](F23.md) | Reactive 3D avatar | DONE | 2/2 |
| [F24](F24.md) | Evaluation lab and regression gates | TODO | 0/5 |
| [F25](F25.md) | Voice, speech and interruption | TODO | 0/5 |
| [F26](F26.md) | Policy dependency visualization | TODO | 0/5 |
| [F27](F27.md) | OCR, DOCX and batch ingestion | TODO | 0/5 |
| [F28](F28.md) | Standard A2A interoperability adapter | TODO | 0/5 |
| [F29](F29.md) | Policy training sandbox | TODO | 0/5 |
