/*
  Additional fictional cases so the index and workspace show every assessment status.
*/
import type { Assessment, CaseDetail, CaseSummary } from "@/lib/api/types";
import { cite } from "./cite";
import { SNAPSHOT_ID } from "./policies";
import { vendorCaseComplete } from "./vendorCase";

function base(a: Partial<Assessment> & Pick<Assessment, "run_id" | "status" | "summary">): Assessment {
  return {
    schema_version: "1.0",
    case_revision_id: `${a.run_id}_rev`,
    policy_snapshot_id: SNAPSHOT_ID,
    as_of: "2026-09-24",
    scope: "Kestrel Mutual demo policy corpus",
    findings: [],
    citations: [],
    risks: [],
    recommendations: [],
    limitations: [],
    review_state: "unreviewed",
    ...a,
  };
}

const contractor: CaseDetail = {
  id: "case_contractor_access",
  title: "Give a contractor temporary production access",
  owner: "Tomasz Wierzbicki",
  business_area: "Technology",
  status: "non_compliant",
  run_state: "completed",
  unresolved_facts: 1,
  review_state: "unreviewed",
  updated_at: "2026-09-24T15:40:00Z",
  as_of: "2026-09-24",
  scope: "Access control policy",
  scenario_text: "A contractor from Fenwick Systems needs production database access for three weeks to finish a migration.",
  policy_snapshot_id: SNAPSHOT_ID,
  messages: [
    { id: "c2_m1", role: "user", text: "A contractor from Fenwick Systems needs production database access for three weeks to finish a migration.", created_at: "2026-09-24T15:38:00Z" },
  ],
  facts: [
    { id: "c2_f1", key: "person_type", label: "Person", value: "Contractor, Fenwick Systems", origin: "provided", confirmed: true },
    { id: "c2_f2", key: "duration", label: "Duration", value: "21 days", origin: "provided", confirmed: true },
    { id: "c2_f3", key: "manager_approval", label: "Manager approval", value: null, origin: "unknown", confirmed: false },
    { id: "c2_f4", key: "nda_on_file", label: "Confidentiality agreement", value: null, origin: "unknown", confirmed: false },
  ],
  latest_run_id: "run_c2",
  pending_questions: [],
  agent_messages: [],
  assessment: base({
    run_id: "run_c2",
    status: "non_compliant",
    summary: "Temporary access is capped at 14 days, and the contractor’s confidentiality agreement is unconfirmed.",
    scope: "Kestrel Mutual demo access control policy",
    citations: [
      cite("c2_cite_1", "ac_v1_2_2.4", "expires automatically after 14 days"),
      cite("c2_cite_2", "ac_v1_2_2.5", "only while a signed confidentiality agreement is on file"),
    ],
    findings: [
      { id: "c2_fd1", requirement_id: "req_ac_2_4", title: "Requested duration exceeds 14 days", status: "violated", rationale: "Temporary access expires after 14 days; 21 days needs a renewal.", fact_ids: ["c2_f2"], citation_ids: ["c2_cite_1"], support: "validated", missing_facts: [] },
      { id: "c2_fd2", requirement_id: "req_ac_2_5", title: "Confidentiality agreement unconfirmed", status: "unknown", rationale: "Contractors need a signed agreement on file. Its status is unknown.", fact_ids: ["c2_f4"], citation_ids: ["c2_cite_2"], support: "validated", missing_facts: ["Signed confidentiality agreement"] },
    ],
    limitations: ["Only the demo access control policy was assessed."],
  }),
};

const pricing: CaseDetail = {
  id: "case_pricing_training",
  title: "Keep old claim records in a pricing model training set",
  owner: "Amara Okafor",
  business_area: "Pricing",
  status: "conflicting_policy",
  run_state: "completed",
  unresolved_facts: 0,
  review_state: "information_requested",
  updated_at: "2026-09-23T11:05:00Z",
  as_of: "2026-09-23",
  scope: "Retention and model development policies",
  scenario_text: "Our motor pricing model was trained on claims that closed eight years ago. Can we keep that training set?",
  policy_snapshot_id: SNAPSHOT_ID,
  messages: [
    { id: "c3_m1", role: "user", text: "Our motor pricing model was trained on claims that closed eight years ago. Can we keep that training set?", created_at: "2026-09-23T11:01:00Z" },
  ],
  facts: [
    { id: "c3_f1", key: "claim_age", label: "Claims closed", value: "8 years ago", origin: "provided", confirmed: true },
    { id: "c3_f2", key: "model_status", label: "Model", value: "In production", origin: "provided", confirmed: true },
  ],
  latest_run_id: "run_c3",
  pending_questions: [],
  agent_messages: [],
  assessment: base({
    run_id: "run_c3",
    as_of: "2026-09-23",
    status: "conflicting_policy",
    summary: "Two applicable policies disagree: one requires deletion after seven years, the other requires keeping training data.",
    citations: [
      cite("c3_cite_1", "rd_v1_5_5.1", "retained for seven years after the claim closes, then deleted"),
      cite("c3_cite_2", "md_v1_2_2.2", "kept for the life of that model plus three years"),
    ],
    findings: [
      { id: "c3_fd1", requirement_id: "req_rd_5_1", title: "Retention limit versus training data rule", status: "conflict", rationale: "Clause 5.1 requires deletion; clause 2.2 requires retention. No reviewed precedence rule resolves this.", fact_ids: ["c3_f1", "c3_f2"], citation_ids: ["c3_cite_1", "c3_cite_2"], support: "validated", missing_facts: [] },
    ],
    recommendations: [
      { id: "c3_a1", finding_ids: ["c3_fd1"], citation_ids: ["c3_cite_1", "c3_cite_2"], action: "Ask the policy owners to record which rule takes precedence for training data.", suggested_role: "Head of Records", completion_criteria: "A reviewed precedence note exists for both clauses.", kind: "mandatory" },
    ],
    review_state: "information_requested",
  }),
};

const engineer: CaseDetail = {
  id: "case_engineer_access",
  title: "Seven-day production access for an on-call engineer",
  owner: "Lena Hoffmann",
  business_area: "Technology",
  status: "compliant_within_scope",
  run_state: "completed",
  unresolved_facts: 0,
  review_state: "accepted",
  updated_at: "2026-09-22T08:20:00Z",
  as_of: "2026-09-22",
  scope: "Access control policy",
  scenario_text: "Staff engineer needs read-only production access for 7 days during an incident rotation. Their manager approved it.",
  policy_snapshot_id: SNAPSHOT_ID,
  messages: [
    { id: "c4_m1", role: "user", text: "Staff engineer needs read-only production access for 7 days during an incident rotation. Their manager approved it.", created_at: "2026-09-22T08:15:00Z" },
  ],
  facts: [
    { id: "c4_f1", key: "duration", label: "Duration", value: "7 days", origin: "provided", confirmed: true },
    { id: "c4_f2", key: "manager_approval", label: "Manager approval", value: "Given", origin: "provided", confirmed: true },
    { id: "c4_f3", key: "access_level", label: "Access level", value: "Read-only", origin: "provided", confirmed: true },
  ],
  latest_run_id: "run_c4",
  pending_questions: [],
  agent_messages: [],
  assessment: base({
    run_id: "run_c4",
    as_of: "2026-09-22",
    status: "compliant_within_scope",
    summary: "Read-only access for 7 days with manager approval meets the access control requirements in scope.",
    scope: "Kestrel Mutual demo access control policy",
    citations: [
      cite("c4_cite_1", "ac_v1_2_2.4", "requires approval from the requester’s line manager"),
      cite("c4_cite_2", "ac_v1_2_2.1", "granted at the lowest level that allows the person to do their assigned work"),
    ],
    findings: [
      { id: "c4_fd1", requirement_id: "req_ac_2_4", title: "Manager approval given, within 14 days", status: "met", rationale: "Approval is recorded and 7 days is inside the limit.", fact_ids: ["c4_f1", "c4_f2"], citation_ids: ["c4_cite_1"], support: "validated", missing_facts: [] },
      { id: "c4_fd2", requirement_id: "req_ac_2_1", title: "Read-only access fits the task", status: "met", rationale: "Incident triage needs read access only.", fact_ids: ["c4_f3"], citation_ids: ["c4_cite_2"], support: "validated", missing_facts: [] },
    ],
    limitations: ["Only the demo access control policy was assessed."],
    review_state: "accepted",
  }),
};

const venue: CaseDetail = {
  id: "case_client_venue",
  title: "Host a client dinner at a restaurant we have not used before",
  owner: "Marcus Adeyemi",
  business_area: "Sales",
  status: "out_of_scope",
  run_state: "completed",
  unresolved_facts: 0,
  review_state: "unreviewed",
  updated_at: "2026-09-21T17:45:00Z",
  as_of: "2026-09-21",
  scope: "Full demo corpus",
  scenario_text: "Can I host a client dinner at a restaurant we have not used before?",
  policy_snapshot_id: SNAPSHOT_ID,
  messages: [
    { id: "c5_m1", role: "user", text: "Can I host a client dinner at a restaurant we have not used before?", created_at: "2026-09-21T17:44:00Z" },
  ],
  facts: [{ id: "c5_f1", key: "activity", label: "Activity", value: "Client hospitality", origin: "provided", confirmed: true }],
  latest_run_id: "run_c5",
  pending_questions: [],
  agent_messages: [],
  assessment: base({
    run_id: "run_c5",
    as_of: "2026-09-21",
    status: "out_of_scope",
    summary: "No policy in the demo corpus covers client hospitality or venue choice. This is not a compliant result.",
    limitations: ["The corpus has no hospitality or gifts policy. Ask the policy owner which policy applies."],
  }),
};

const laptop: CaseSummary = {
  id: "case_remote_laptop",
  title: "Handle claims from a personal laptop while travelling",
  owner: "Priya Raman",
  business_area: "Claims",
  status: null,
  run_state: "waiting_for_user",
  unresolved_facts: 3,
  review_state: "unreviewed",
  updated_at: "2026-09-25T08:02:00Z",
};

export const caseDetails: Record<string, CaseDetail> = {
  [vendorCaseComplete.id]: vendorCaseComplete,
  [contractor.id]: contractor,
  [pricing.id]: pricing,
  [engineer.id]: engineer,
  [venue.id]: venue,
};

function toSummary(c: CaseDetail): CaseSummary {
  const { id, title, owner, business_area, status, run_state, unresolved_facts, review_state, updated_at } = c;
  return { id, title, owner, business_area, status, run_state, unresolved_facts, review_state, updated_at };
}

export const caseSummaries: CaseSummary[] = [
  toSummary(vendorCaseComplete),
  laptop,
  toSummary(contractor),
  toSummary(pricing),
  toSummary(engineer),
  toSummary(venue),
];
