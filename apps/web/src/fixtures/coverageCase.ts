/* Shared test fixture, not a live model result. Exercises a retrieved but omitted clause. */
import type { Assessment, CaseDetail } from "@/lib/api/types";
import { vendorCaseComplete, vendorAssessment } from "./vendorCase";

export const coverageGapAssessment: Assessment = {
  ...vendorAssessment,
  run_id: "run_coverage_fixture",
  as_of: "2026-10-01",
  status: "insufficient_information",
  summary: "One retrieved requirement candidate has no confirmed assessment or justified exclusion. A compliant result is withheld until this coverage gap is reviewed.",
  findings: [{
    ...vendorAssessment.findings[0],
    requirement_id: "ds_v2_4_4.2",
    title: "Data-owner approval is recorded",
    status: "met",
    rationale: "Written data-owner approval was recorded before transfer.",
    citation_ids: ["cite_coverage_approval"],
  }],
  citations: [{
    id: "cite_coverage_approval", policy_version_id: "ds_v2", clause_id: "ds_v2_4_4.2",
    page_index: 1, section_path: ["4", "4.2"],
    quote: "requires written approval from the data owner",
    source_url: "/api/v1/policy-versions/ds_v2/source?page=2",
  }],
  risks: [],
  recommendations: [],
  limitations: ["Fictional Kestrel Mutual policies in snapshot_demo_v1, effective on 1 October 2026. Coverage accounts for retrieved candidates only."],
  confidence: null,
  coverage: {
    gate_version: "retrieved-candidates-v1",
    candidate_count: 2,
    accounted_count: 1,
    unresolved_clause_ids: ["ds_v2_4_4.5"],
    rows: [
      {
        clause_id: "ds_v2_4_4.2", policy_title: "Customer Data Sharing Policy",
        policy_version_id: "ds_v2", version_label: "v2", section: "4.2",
        heading: "Data-owner approval", page_index: 1,
        text: "External sharing of customer data requires written approval from the data owner, recorded in the data-sharing register before any transfer takes place.",
        source_url: "/api/v1/policy-versions/ds_v2/source?page=2",
        retrieval_reason: "search", candidate_basis: "clause_kind", finding_ids: ["finding_1"],
        state: "assessed", note: "Written data-owner approval was recorded before transfer.",
      },
      {
        clause_id: "ds_v2_4_4.5", policy_title: "Customer Data Sharing Policy",
        policy_version_id: "ds_v2", version_label: "v2", section: "4.5",
        heading: "Retention period", page_index: 1,
        text: "Each external share must record a retention period, after which the recipient deletes or returns the data and confirms this in writing.",
        source_url: "/api/v1/policy-versions/ds_v2/source?page=2",
        retrieval_reason: "search", candidate_basis: "clause_kind", finding_ids: [],
        state: "unassessed", note: "The analysis emitted no finding for this retrieved candidate.",
      },
    ],
  },
};

export const coverageGapCase: CaseDetail = {
  ...vendorCaseComplete,
  id: "case_coverage_fixture",
  title: "External sharing with an unassessed retention requirement",
  as_of: coverageGapAssessment.as_of,
  status: coverageGapAssessment.status,
  latest_run_id: coverageGapAssessment.run_id,
  assessment: coverageGapAssessment,
  scenario_text: "We plan to share customer data with an external analytics vendor. Written data-owner approval was recorded before transfer. Retention terms have not been discussed.",
  facts: vendorCaseComplete.facts.map((fact) => fact.key === "data_owner_approval"
    ? { ...fact, value: "Recorded before transfer" } : fact),
};
