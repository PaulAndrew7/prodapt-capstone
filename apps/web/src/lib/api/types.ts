/*
  Frontend mirror of the contracts in IMPLEMENTATION_PLAN.md section 5.
  Replace with generated types from packages/contracts once F00 lands;
  keep field names identical so the swap is mechanical.
*/

export type AssessmentStatus =
  | "non_compliant"
  | "conflicting_policy"
  | "insufficient_information"
  | "compliant_within_scope"
  | "out_of_scope";

export type RequirementStatus =
  | "met"
  | "violated"
  | "unknown"
  | "not_applicable"
  | "conflict";

export type SupportState = "validated" | "unsupported" | "contradicted" | "pending";

export type FactOrigin = "provided" | "inferred" | "unknown";

export type RunState =
  | "queued"
  | "running"
  | "waiting_for_user"
  | "completed"
  | "failed"
  | "canceled";

export type AgentRole =
  | "retrieval"
  | "analysis"
  | "risk"
  | "validation"
  | "recommendation";

export type ReviewState = "unreviewed" | "accepted" | "challenged" | "information_requested";

export interface Policy {
  id: string;
  title: string;
  category: string;
  business_area: string;
  owner: string;
  active_version_id: string;
  versions: PolicyVersionSummary[];
}

export interface PolicyVersionSummary {
  id: string;
  label: string;
  effective_from: string;
  effective_to: string | null;
  status: "published" | "draft" | "superseded";
  index_status: "ready" | "indexing" | "failed";
  pages: number;
}

export interface Clause {
  id: string;
  policy_id: string;
  policy_version_id: string;
  section_path: string[];
  heading: string;
  text: string;
  page_index: number;
  kind: "definition" | "requirement" | "exception" | "general";
}

export interface PolicyVersion extends PolicyVersionSummary {
  policy_id: string;
  policy_title: string;
  clauses: Clause[];
  extraction_warnings: string[];
}

export interface Citation {
  id: string;
  policy_version_id: string;
  clause_id: string;
  page_index: number;
  section_path: string[];
  quote: string;
  source_url: string;
}

export interface Fact {
  id: string;
  key: string;
  label: string;
  value: string | null;
  origin: FactOrigin;
  confirmed: boolean;
  source_message_id?: string;
}

export interface Finding {
  id: string;
  requirement_id: string;
  title: string;
  status: RequirementStatus;
  rationale: string;
  fact_ids: string[];
  citation_ids: string[];
  support: SupportState;
  missing_facts: string[];
}

export interface Risk {
  id: string;
  finding_ids: string[];
  severity: "critical" | "high" | "medium" | "low";
  likelihood: "unknown" | "low" | "medium" | "high";
  description: string;
  rubric_version: string;
}

export interface Recommendation {
  id: string;
  finding_ids: string[];
  citation_ids: string[];
  action: string;
  suggested_role: string;
  completion_criteria: string;
  kind: "mandatory" | "optional";
}

export interface Assessment {
  schema_version: "1.0";
  run_id: string;
  case_revision_id: string;
  policy_snapshot_id: string;
  as_of: string;
  status: AssessmentStatus;
  scope: string;
  summary: string;
  findings: Finding[];
  citations: Citation[];
  risks: Risk[];
  recommendations: Recommendation[];
  limitations: string[];
  review_state: ReviewState;
  hypothetical?: boolean;
}

export interface ClarificationQuestion {
  id: string;
  question: string;
  reason: string;
  clause_ref: string;
  fact_key: string;
  answer_kind: "choice" | "text";
  choices?: string[];
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  created_at: string;
}

export interface AgentMessage {
  message_id: string;
  sender: AgentRole;
  recipient: AgentRole | "gate";
  type: string;
  summary: string;
  causal_parent_id: string | null;
  at_ms: number;
}

export interface RunEvent {
  event_id: string;
  run_id: string;
  sequence: number;
  occurred_at: string;
  schema_version: "1.0";
  type:
    | "run.queued"
    | "run.started"
    | "retrieval.completed"
    | "analysis.completed"
    | "risk.completed"
    | "validation.completed"
    | "recommendation.completed"
    | "clarification.required"
    | "run.resumed"
    | "run.completed"
    | "run.failed"
    | "run.canceled";
  payload: Record<string, unknown>;
}

export interface CaseSummary {
  id: string;
  title: string;
  owner: string;
  business_area: string;
  status: AssessmentStatus | null;
  run_state: RunState | null;
  unresolved_facts: number;
  review_state: ReviewState;
  updated_at: string;
}

export interface CaseDetail extends CaseSummary {
  as_of: string;
  scope: string;
  scenario_text: string;
  policy_snapshot_id: string;
  messages: Message[];
  facts: Fact[];
  latest_run_id: string | null;
  assessment: Assessment | null;
  pending_questions: ClarificationQuestion[];
  agent_messages: AgentMessage[];
}

export interface LookupAnswer {
  question: string;
  answer: string;
  citations: Citation[];
  support: SupportState;
  snapshot_id: string;
}

export interface ApiError {
  code: string;
  message: string;
  request_id: string;
  retryable: boolean;
}
