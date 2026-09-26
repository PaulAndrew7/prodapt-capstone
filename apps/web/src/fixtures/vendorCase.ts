/*
  The worked scenario from IMPLEMENTATION_PLAN.md section 10, as fixtures.
  Fictional organization, vendor and people. Used by FixtureApi and the front-door exhibits.
*/
import type {
  AgentMessage,
  Assessment,
  CaseDetail,
  Citation,
  ClarificationQuestion,
  Fact,
  Message,
  RunEvent,
} from "@/lib/api/types";
import { SNAPSHOT_ID } from "./policies";
import { cite } from "./cite";

export const VENDOR_CASE_ID = "case_vendor_share";
export const VENDOR_RUN_ID = "run_demo_001";

export const VENDOR_SCENARIO =
  "We want to send customer records to a new analytics vendor, Brightline Analytics. The data owner has not approved it. I don’t know whether vendor review is complete.";

export const vendorCitations: Citation[] = [
  cite("cite_1", "ds_v1_4_4.2", "requires written approval from the data owner, recorded in the data-sharing register before any transfer takes place"),
  cite("cite_2", "vd_v1_3_3.1", "hold Approved status in the vendor register, before receiving customer data"),
  cite("cite_3", "ds_v1_4_4.3", "The purpose and the field list must be recorded with the approval"),
  cite("cite_4", "ds_v1_4_4.4", "Transfers required by law or by a regulator’s written request follow the Legal Disclosure Procedure"),
  cite("cite_5", "ds_v1_4_4.1", "any transfer of, or remote access to, customer data by a party outside Kestrel Mutual, including vendors"),
];

export const vendorMessages: Message[] = [
  { id: "msg_1", role: "user", text: VENDOR_SCENARIO, created_at: "2026-09-25T09:12:00Z" },
  { id: "msg_2", role: "assistant", text: "Two facts decide this case. I have two questions before I assess it.", created_at: "2026-09-25T09:12:09Z" },
];

export const vendorFactsInitial: Fact[] = [
  { id: "fact_recipient", key: "recipient", label: "Recipient", value: "Brightline Analytics, external vendor", origin: "provided", confirmed: true, source_message_id: "msg_1" },
  { id: "fact_approval_absent", key: "data_owner_approval", label: "Data-owner approval", value: "Not given", origin: "provided", confirmed: true, source_message_id: "msg_1" },
  { id: "fact_purpose", key: "purpose", label: "Purpose", value: "Marketing analytics", origin: "inferred", confirmed: false, source_message_id: "msg_1" },
  { id: "fact_vendor_review", key: "vendor_review_status", label: "Vendor review", value: null, origin: "unknown", confirmed: false },
  { id: "fact_fields", key: "fields_shared", label: "Fields shared", value: null, origin: "unknown", confirmed: false },
];

export const vendorQuestions: ClarificationQuestion[] = [
  {
    id: "q_vendor_review",
    question: "Does Brightline Analytics hold Approved status in the vendor register?",
    reason: "Clause 3.1 blocks customer data from reaching a vendor without an approved review.",
    clause_ref: "vd_v1_3_3.1",
    fact_key: "vendor_review_status",
    answer_kind: "choice",
    choices: ["Yes, approved", "No, not approved"],
  },
  {
    id: "q_fields",
    question: "Which customer fields will you share, and for what purpose?",
    reason: "Clause 4.3 limits the fields to those the documented purpose needs.",
    clause_ref: "ds_v1_4_4.3",
    fact_key: "fields_shared",
    answer_kind: "text",
  },
];

export const vendorAnswers: Record<string, string | null> = {
  q_vendor_review: null,
  q_fields: "Customer ID, postcode and product holdings, for churn modelling.",
};

export const vendorFactsFinal: Fact[] = [
  vendorFactsInitial[0],
  vendorFactsInitial[1],
  { ...vendorFactsInitial[2], value: "Churn modelling", origin: "provided", confirmed: true, source_message_id: "msg_4" },
  { ...vendorFactsInitial[3], value: null, origin: "unknown", confirmed: true, source_message_id: "msg_4" },
  { ...vendorFactsInitial[4], value: "Customer ID, postcode, product holdings", origin: "provided", confirmed: true, source_message_id: "msg_4" },
];

export const vendorAssessment: Assessment = {
  schema_version: "1.0",
  run_id: VENDOR_RUN_ID,
  case_revision_id: "scenario_002",
  policy_snapshot_id: SNAPSHOT_ID,
  as_of: "2026-09-25",
  status: "non_compliant",
  scope: "Kestrel Mutual demo data-sharing and vendor policies",
  summary: "The plan shares customer data externally without the data-owner approval that clause 4.2 requires.",
  findings: [
    {
      id: "finding_1",
      requirement_id: "req_ds_4_2",
      title: "Data-owner approval is absent",
      status: "violated",
      rationale: "You stated the data owner has not approved the share. Clause 4.2 requires recorded approval before any transfer.",
      fact_ids: ["fact_approval_absent", "fact_recipient"],
      citation_ids: ["cite_1", "cite_5"],
      support: "validated",
      missing_facts: [],
    },
    {
      id: "finding_2",
      requirement_id: "req_vd_3_1",
      title: "Vendor review status is unknown",
      status: "unknown",
      rationale: "Brightline Analytics must hold Approved status before receiving customer data. Nobody has confirmed its status.",
      fact_ids: ["fact_vendor_review"],
      citation_ids: ["cite_2"],
      support: "validated",
      missing_facts: ["Vendor register status for Brightline Analytics"],
    },
    {
      id: "finding_3",
      requirement_id: "req_ds_4_3",
      title: "Purpose and fields are not yet recorded",
      status: "unknown",
      rationale: "You named the fields and the purpose, but clause 4.3 needs them recorded with an approval, which does not exist yet.",
      fact_ids: ["fact_fields", "fact_purpose"],
      citation_ids: ["cite_3"],
      support: "validated",
      missing_facts: ["Recorded purpose and field list"],
    },
    {
      id: "finding_4",
      requirement_id: "req_ds_4_4",
      title: "Legal disclosure exception does not apply",
      status: "not_applicable",
      rationale: "No law or regulator request is involved, so the exception in clause 4.4 is not triggered.",
      fact_ids: ["fact_purpose"],
      citation_ids: ["cite_4"],
      support: "validated",
      missing_facts: [],
    },
  ],
  citations: vendorCitations,
  risks: [
    { id: "risk_1", finding_ids: ["finding_1"], severity: "high", likelihood: "unknown", description: "Customer data would leave the organization without the owner’s recorded approval.", rubric_version: "demo-risk-v1" },
    { id: "risk_2", finding_ids: ["finding_2"], severity: "medium", likelihood: "unknown", description: "If the vendor is unreviewed, data would reach a party whose controls nobody has checked.", rubric_version: "demo-risk-v1" },
  ],
  recommendations: [
    { id: "action_1", finding_ids: ["finding_1"], citation_ids: ["cite_1"], action: "Get written approval from the data owner and record it in the data-sharing register before any transfer.", suggested_role: "Data owner", completion_criteria: "An approval entry for this share exists in the register.", kind: "mandatory" },
    { id: "action_2", finding_ids: ["finding_2"], citation_ids: ["cite_2"], action: "Confirm Brightline Analytics holds Approved status in the vendor register. If it does not, start a vendor review.", suggested_role: "Vendor management", completion_criteria: "The register shows Approved status within the last twelve months.", kind: "mandatory" },
    { id: "action_3", finding_ids: ["finding_3"], citation_ids: ["cite_3"], action: "Record the purpose (churn modelling) and the three fields with the approval.", suggested_role: "Requester", completion_criteria: "The register entry lists the purpose and the field list.", kind: "mandatory" },
  ],
  limitations: [
    "Only Kestrel Mutual’s demo data-sharing and vendor policies were assessed.",
    "Results use policy snapshot snapshot_demo_v1 as of 25 Sep 2026.",
  ],
  review_state: "unreviewed",
};

/* Hypothetical branch: approval recorded, vendor approved, purpose and fields recorded. */
export const vendorHypothetical: Assessment = {
  ...vendorAssessment,
  run_id: "run_demo_002",
  case_revision_id: "scenario_003_hypothetical",
  status: "compliant_within_scope",
  hypothetical: true,
  summary: "With approval recorded, an approved vendor and a documented field list, the share meets every requirement in scope.",
  findings: vendorAssessment.findings.map((f) =>
    f.status === "not_applicable"
      ? f
      : {
          ...f,
          status: "met" as const,
          missing_facts: [],
          title:
            f.id === "finding_1"
              ? "Data-owner approval is recorded"
              : f.id === "finding_2"
                ? "Vendor holds Approved status"
                : "Purpose and fields are recorded",
          rationale: "Met under the hypothetical facts in this branch.",
        },
  ),
  risks: [],
  recommendations: [],
  limitations: [
    "Hypothetical branch. These facts are assumptions, not the real case.",
    ...vendorAssessment.limitations,
  ],
};

export const vendorHypotheticalChanges = [
  { label: "Data-owner approval", from: "Not given", to: "Recorded in register" },
  { label: "Vendor review", from: "Unknown", to: "Approved" },
  { label: "Purpose and fields", from: "Stated only", to: "Recorded with approval" },
];

export const vendorAgentMessages: AgentMessage[] = [
  { message_id: "am_1", sender: "retrieval", recipient: "analysis", type: "evidence_bundle", summary: "6 clauses from 2 policies in snapshot_demo_v1", causal_parent_id: null, at_ms: 740 },
  { message_id: "am_2", sender: "analysis", recipient: "risk", type: "findings", summary: "4 requirements checked, 1 violated, 2 unknown, 1 not applicable", causal_parent_id: "am_1", at_ms: 3120 },
  { message_id: "am_3", sender: "risk", recipient: "validation", type: "risks", summary: "1 high, 1 medium; likelihood unknown for both", causal_parent_id: "am_2", at_ms: 3890 },
  { message_id: "am_4", sender: "validation", recipient: "retrieval", type: "evidence_request", summary: "Needs the definition of external sharing to support finding 1", causal_parent_id: "am_3", at_ms: 5210 },
  { message_id: "am_5", sender: "retrieval", recipient: "validation", type: "evidence_bundle", summary: "Added clause 4.1, definition of external sharing", causal_parent_id: "am_4", at_ms: 5630 },
  { message_id: "am_6", sender: "validation", recipient: "recommendation", type: "validated_findings", summary: "All 4 findings supported by cited text", causal_parent_id: "am_5", at_ms: 6940 },
  { message_id: "am_7", sender: "recommendation", recipient: "gate", type: "recommendations", summary: "3 mandatory actions, each linked to a gap and a clause", causal_parent_id: "am_6", at_ms: 8410 },
];

export const vendorCaseComplete: CaseDetail = {
  id: VENDOR_CASE_ID,
  title: "Share customer records with a new analytics vendor",
  owner: "Priya Raman",
  business_area: "Marketing analytics",
  status: "non_compliant",
  run_state: "completed",
  unresolved_facts: 1,
  review_state: "unreviewed",
  updated_at: "2026-09-25T09:14:31Z",
  as_of: "2026-09-25",
  scope: "Data sharing and vendor policies",
  scenario_text: VENDOR_SCENARIO,
  policy_snapshot_id: SNAPSHOT_ID,
  messages: [
    ...vendorMessages,
    { id: "msg_3", role: "assistant", text: "Does Brightline Analytics hold Approved status in the vendor register? Which customer fields will you share, and for what purpose?", created_at: "2026-09-25T09:12:10Z" },
    { id: "msg_4", role: "user", text: "I don’t know about the vendor review. Customer ID, postcode and product holdings, for churn modelling.", created_at: "2026-09-25T09:13:02Z" },
  ],
  facts: vendorFactsFinal,
  latest_run_id: VENDOR_RUN_ID,
  assessment: vendorAssessment,
  pending_questions: [],
  agent_messages: vendorAgentMessages,
};

type ScriptStep = { after_ms: number; type: RunEvent["type"]; payload?: Record<string, unknown> };

/* Event timings for FixtureApi. Pauses at clarification until answers arrive. */
export const vendorScriptBeforeClarification: ScriptStep[] = [
  { after_ms: 0, type: "run.queued" },
  { after_ms: 350, type: "run.started" },
  { after_ms: 1100, type: "retrieval.completed", payload: { clauses: 6, policies: 2 } },
  { after_ms: 2300, type: "analysis.completed", payload: { requirements: 4, missing_facts: 2 } },
  { after_ms: 600, type: "clarification.required", payload: { question_ids: vendorQuestions.map((q) => q.id) } },
];

export const vendorScriptAfterClarification: ScriptStep[] = [
  { after_ms: 0, type: "run.resumed" },
  { after_ms: 1500, type: "analysis.completed", payload: { requirements: 4, missing_facts: 1 } },
  { after_ms: 800, type: "risk.completed", payload: { risks: 2 } },
  { after_ms: 1400, type: "validation.completed", payload: { supported: 4, repairs: 1 } },
  { after_ms: 1300, type: "recommendation.completed", payload: { actions: 3 } },
  { after_ms: 400, type: "run.completed", payload: { status: "non_compliant" } },
];

export type { ScriptStep };
