import type { Assessment, CaseDetail, ClarificationQuestion } from "@/lib/api/types";
import { coverageGapAssessment, coverageGapCase } from "./coverageCase";

// UI/contract fixture only. Runtime local results come from the backend's source checks.
const rows = coverageGapAssessment.coverage!.rows;
export const localReviewAssessment: Assessment = {
  ...coverageGapAssessment,
  run_id: "run_local_review_fixture",
  confidence: null,
  execution: { mode: "local_review", reason: "model_failure", engine_version: "local-review-v1", failed_stage: "analysis", error_code: "model_timeout" },
  summary: "Local review cannot establish a complete result: 2 retrieved checks remain unknown. These are unconfirmed dispositions, not established breaches or necessarily missing narrative facts.",
  findings: rows.map((row, i) => ({
    id: `local_finding_${i}`, requirement_id: row.clause_id, title: row.heading,
    status: "unknown", support: "validated", confidence: null,
    rationale: "Local review has not established applicability or satisfaction. Narrative text is not semantically interpreted in this mode; an unknown check is not a breach.",
    fact_ids: [`local_fact_${i}`], citation_ids: [`local_cite_${i}`], missing_facts: ["Confirm whether this clause applies and is satisfied."],
  })),
  citations: rows.map((row, i) => ({ id: `local_cite_${i}`, clause_id: row.clause_id, policy_version_id: row.policy_version_id,
    page_index: row.page_index, section_path: ["4", row.section], quote: row.text, source_url: row.source_url })),
  risks: [], recommendations: [],
  coverage: { ...coverageGapAssessment.coverage!, accounted_count: rows.length, unresolved_clause_ids: [],
    rows: rows.map((row, i) => ({ ...row, finding_ids: [`local_finding_${i}`], state: "assessed", note: "Local disposition remains unknown." })) },
  limitations: [coverageGapAssessment.limitations[0], "Local review uses source checks and explicit user confirmations. No model semantically validated this result. Unreviewed interpretations stay unknown."],
};
export const localReviewCase: CaseDetail = {
  ...coverageGapCase, id: "case_local_review_fixture", latest_run_id: localReviewAssessment.run_id,
  execution: localReviewAssessment.execution, assessment: localReviewAssessment,
  facts: rows.map((row, i) => ({ id: `local_fact_${i}`, key: `offline_${row.clause_id}`,
    label: `Local confirmation: ${row.policy_title} §${row.section}`, value: null, origin: "unknown", confirmed: false, source_message_id: null })),
};
export const localReviewQuestions: ClarificationQuestion[] = rows.map((row) => ({
  id: `offline_${row.clause_id}`, fact_key: `offline_${row.clause_id}`, clause_ref: row.clause_id,
  question: `What can you confirm for ${row.policy_title} §${row.section}: ${row.heading}?`,
  reason: "Read the cited clause before choosing. This records your assessment of its condition and requirement.",
  answer_kind: "choice", choices: ["Applies and is satisfied", "Applies and is breached", "Does not apply"],
}));
