/*
  Fictional demo corpus for "Kestrel Mutual", an invented insurer.
  Not real policy, law or regulatory guidance. Answer keys never live here.
*/
import type { Clause, Policy, PolicyVersion } from "@/lib/api/types";

export const ORG_NAME = "Kestrel Mutual";
export const SNAPSHOT_ID = "snapshot_demo_v1";

function clause(
  versionId: string,
  policyId: string,
  path: string[],
  heading: string,
  text: string,
  page: number,
  kind: Clause["kind"] = "requirement",
): Clause {
  return {
    id: `${versionId}_${path.join("_")}`,
    policy_id: policyId,
    policy_version_id: versionId,
    section_path: path,
    heading,
    text,
    page_index: page,
    kind,
  };
}

const dsV1Clauses: Clause[] = [
  clause("ds_v1", "ds", ["1"], "Purpose", "This policy sets the conditions under which Kestrel Mutual may share customer data with any party outside the organization.", 0, "general"),
  clause("ds_v1", "ds", ["4", "4.1"], "Definition of external sharing", "“External sharing” means any transfer of, or remote access to, customer data by a party outside Kestrel Mutual, including vendors and affiliates operating as a separate legal entity.", 2, "definition"),
  clause("ds_v1", "ds", ["4", "4.2"], "Data-owner approval", "External sharing of customer data requires written approval from the data owner, recorded in the data-sharing register before any transfer takes place.", 2),
  clause("ds_v1", "ds", ["4", "4.3"], "Purpose limitation", "The fields shared must be limited to those necessary for the documented purpose of the sharing. The purpose and the field list must be recorded with the approval.", 2),
  clause("ds_v1", "ds", ["4", "4.4"], "Legal disclosure exception", "Transfers required by law or by a regulator’s written request follow the Legal Disclosure Procedure instead of clause 4.2. Legal is the approver for these transfers.", 3, "exception"),
  clause("ds_v1", "ds", ["5", "5.1"], "Register upkeep", "The data owner reviews each open entry in the data-sharing register every twelve months and closes entries for sharing that has ended.", 3),
];

const dsV2Clauses: Clause[] = [
  ...dsV1Clauses.map((c) => ({
    ...c,
    id: c.id.replace("ds_v1", "ds_v2"),
    policy_version_id: "ds_v2",
  })),
  clause("ds_v2", "ds", ["4", "4.5"], "Retention period", "Each external share must record a retention period, after which the recipient deletes or returns the data and confirms this in writing.", 3),
];

const vdV1Clauses: Clause[] = [
  clause("vd_v1", "vd", ["1"], "Scope", "This policy applies to every third party that will receive, store or process Kestrel Mutual customer data.", 0, "general"),
  clause("vd_v1", "vd", ["3", "3.1"], "Review before data access", "A vendor must complete Kestrel Mutual’s vendor review, and hold Approved status in the vendor register, before receiving customer data.", 1),
  clause("vd_v1", "vd", ["3", "3.2"], "Review content", "Vendor review covers security controls, data location and subprocessors. A completed review is valid for twelve months from its approval date.", 1),
  clause("vd_v1", "vd", ["3", "3.3"], "Expired reviews", "A vendor whose review has expired is treated as unreviewed until a new review is approved.", 1),
];

const acV1Clauses: Clause[] = [
  clause("ac_v1", "ac", ["2", "2.1"], "Least privilege", "Access to production systems holding customer data is granted at the lowest level that allows the person to do their assigned work.", 1),
  clause("ac_v1", "ac", ["2", "2.4"], "Temporary access", "Temporary production access requires approval from the requester’s line manager and expires automatically after 14 days.", 1),
  clause("ac_v1", "ac", ["2", "2.5"], "Contractors", "Contractors may hold temporary production access only while a signed confidentiality agreement is on file.", 2),
];

const rdV1Clauses: Clause[] = [
  clause("rd_v1", "rd", ["5", "5.1"], "Standard retention", "Customer claim records are retained for seven years after the claim closes, then deleted.", 1),
  clause("rd_v1", "rd", ["5", "5.3"], "Deletion holds", "Records under a litigation or regulatory hold must not be deleted until Legal releases the hold, regardless of any deletion request.", 2, "exception"),
];

const mdV1Clauses: Clause[] = [
  clause("md_v1", "md", ["2", "2.2"], "Training data retention", "Datasets used to train a pricing model are kept for the life of that model plus three years, so that its outputs can be reproduced.", 1),
];

export const policyVersions: Record<string, PolicyVersion> = {
  md_v1: { id: "md_v1", policy_id: "md", policy_title: "Model Development Standard", label: "v1", effective_from: "2026-02-01", effective_to: null, status: "published", index_status: "ready", pages: 5, clauses: mdV1Clauses, extraction_warnings: [] },
  ds_v1: { id: "ds_v1", policy_id: "ds", policy_title: "Customer Data Sharing Policy", label: "v1", effective_from: "2026-01-01", effective_to: "2026-09-30", status: "published", index_status: "ready", pages: 4, clauses: dsV1Clauses, extraction_warnings: [] },
  ds_v2: { id: "ds_v2", policy_id: "ds", policy_title: "Customer Data Sharing Policy", label: "v2", effective_from: "2026-10-01", effective_to: null, status: "published", index_status: "ready", pages: 4, clauses: dsV2Clauses, extraction_warnings: [] },
  vd_v1: { id: "vd_v1", policy_id: "vd", policy_title: "Vendor Due Diligence Policy", label: "v1", effective_from: "2025-07-01", effective_to: null, status: "published", index_status: "ready", pages: 3, clauses: vdV1Clauses, extraction_warnings: [] },
  ac_v1: { id: "ac_v1", policy_id: "ac", policy_title: "Access Control Policy", label: "v1", effective_from: "2025-11-15", effective_to: null, status: "published", index_status: "ready", pages: 5, clauses: acV1Clauses, extraction_warnings: ["Page 4 contains a table that was extracted as plain text. Check clause 3.2 against the original page."] },
  rd_v1: { id: "rd_v1", policy_id: "rd", policy_title: "Retention and Deletion Policy", label: "v1", effective_from: "2025-04-01", effective_to: null, status: "published", index_status: "ready", pages: 6, clauses: rdV1Clauses, extraction_warnings: [] },
};

function summary(v: PolicyVersion) {
  const { clauses: _c, extraction_warnings: _w, policy_id: _p, policy_title: _t, ...rest } = v;
  return rest;
}

export const policies: Policy[] = [
  { id: "ds", title: "Customer Data Sharing Policy", category: "Data protection", business_area: "All customer-facing teams", owner: "Chief Data Officer", active_version_id: "ds_v1", versions: [summary(policyVersions.ds_v1), summary(policyVersions.ds_v2)] },
  { id: "vd", title: "Vendor Due Diligence Policy", category: "Third-party risk", business_area: "Procurement", owner: "Head of Vendor Management", active_version_id: "vd_v1", versions: [summary(policyVersions.vd_v1)] },
  { id: "ac", title: "Access Control Policy", category: "Information security", business_area: "Technology", owner: "Chief Information Security Officer", active_version_id: "ac_v1", versions: [summary(policyVersions.ac_v1)] },
  { id: "rd", title: "Retention and Deletion Policy", category: "Records management", business_area: "Claims", owner: "Head of Records", active_version_id: "rd_v1", versions: [summary(policyVersions.rd_v1)] },
  { id: "md", title: "Model Development Standard", category: "Data science", business_area: "Pricing", owner: "Head of Actuarial Modelling", active_version_id: "md_v1", versions: [summary(policyVersions.md_v1)] },
  { id: "ir", title: "Incident Response Policy", category: "Information security", business_area: "Technology", owner: "Chief Information Security Officer", active_version_id: "ir_v1", versions: [{ id: "ir_v1", label: "v1", effective_from: "2025-09-01", effective_to: null, status: "published", index_status: "ready", pages: 7 }] },
  { id: "rw", title: "Remote Working Policy", category: "Workplace", business_area: "All staff", owner: "Head of People", active_version_id: "rw_v1", versions: [{ id: "rw_v1", label: "v1", effective_from: "2025-02-10", effective_to: null, status: "published", index_status: "ready", pages: 3 }] },
  { id: "ea", title: "Expense Approval Policy", category: "Finance", business_area: "All staff", owner: "Financial Controller", active_version_id: "ea_v2", versions: [{ id: "ea_v2", label: "v2", effective_from: "2026-04-01", effective_to: null, status: "published", index_status: "ready", pages: 4 }] },
  { id: "cm", title: "Change Management Policy", category: "Information security", business_area: "Technology", owner: "Head of Platform", active_version_id: "cm_v1", versions: [{ id: "cm_v1", label: "v1", effective_from: "2025-06-01", effective_to: null, status: "published", index_status: "ready", pages: 5 }, { id: "cm_v2", label: "v2", effective_from: "2026-11-01", effective_to: null, status: "draft", index_status: "indexing", pages: 5 }] },
  { id: "co", title: "Customer Onboarding Policy", category: "Financial crime", business_area: "Sales", owner: "Money Laundering Reporting Officer", active_version_id: "co_v1", versions: [{ id: "co_v1", label: "v1", effective_from: "2025-03-01", effective_to: null, status: "published", index_status: "ready", pages: 8 }] },
];

export function clauseById(id: string): Clause | undefined {
  for (const v of Object.values(policyVersions)) {
    const c = v.clauses.find((c) => c.id === id);
    if (c) return c;
  }
  return undefined;
}

export function clauseRef(c: Pick<Clause, "section_path" | "policy_version_id">): string {
  const label = policyVersions[c.policy_version_id]?.label ?? "";
  return `§${c.section_path[c.section_path.length - 1]} ${label}`.trim();
}
