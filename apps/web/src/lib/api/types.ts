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
  active_version_id: string | null;
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

export interface UploadPolicyInput {
  policy_id?: string | null;
  title?: string;
  category?: string;
  business_area?: string;
  owner?: string;
  label: string;
  effective_from: string;
  effective_to: string | null;
}
export interface ClauseReview { kind: Clause["kind"]; candidate: boolean }
export interface RelationReview {
  source_clause_id: string;
  target_clause_id: string;
  relation: "references" | "excepts" | "overrides";
  approved: boolean;
  rationale: string;
}
export interface StoredRelation extends RelationReview {
  id: string;
  source_heading: string;
  target_heading: string;
  target_version_id: string;
  provenance: string;
}
export interface DraftReviewInput {
  label: string;
  effective_from: string;
  effective_to: string | null;
  expected_revision: number;
  clauses: Record<string, ClauseReview>;
  relations: RelationReview[];
  review_confirmed: boolean;
  acknowledge_warnings: boolean;
}
export interface DraftReview {
  version: PolicyVersion;
  candidate_clause_ids: string[];
  relations: StoredRelation[];
  revision: number;
  review_complete: boolean;
  warnings_acknowledged: boolean;
  reviewed_at: string | null;
  source_sha256: string;
}
export interface Publication { version_id: string; snapshot_id: string; published_at: string }
export interface GraphNode {
  id: string;
  kind: "policy" | "version" | "clause" | "case" | "finding";
  label: string;
  href: string;
  text: string | null;
  source_url: string | null;
  status: string | null;
}
export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  kind: "contains" | "references" | "excepts" | "overrides" | "supports";
  approved: boolean;
  provenance: string;
}
export interface PolicyGraph {
  snapshot_id: string;
  as_of: string;
  policy_id: string | null;
  case_id: string | null;
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
  total_clauses: number;
}
export interface GraphInput { policy_id?: string; as_of?: string; snapshot_id?: string; case_id?: string }

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
  source_message_id?: string | null;
}

/* Evidence score computed by the API from recorded checks; not a probability. */
export interface ConfidenceFactor {
  label: string;
  points: number;
  max_points: number;
}

export interface Confidence {
  score: number;
  band: "high" | "medium" | "low";
  basis: string;
  factors: ConfidenceFactor[];
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
  confidence?: Confidence | null;
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

export interface CoverageRow {
  clause_id: string;
  policy_title: string;
  policy_version_id: string;
  version_label: string;
  section: string;
  heading: string;
  text: string;
  page_index: number;
  source_url: string;
  retrieval_reason: string;
  candidate_basis: "clause_kind" | "reviewed_corpus" | "proposed_finding";
  finding_ids: string[];
  state: "assessed" | "not_applicable" | "unassessed" | "unconfirmed";
  note: string;
}

export interface EvidenceCoverage {
  gate_version: "retrieved-candidates-v1";
  candidate_count: number;
  accounted_count: number;
  unresolved_clause_ids: string[];
  rows: CoverageRow[];
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
  confidence?: Confidence | null;
  coverage?: EvidenceCoverage | null;
  execution?: ExecutionInfo | null;
}

export interface ExecutionInfo {
  mode: "llm" | "local_review";
  reason: "configured_model" | "no_model" | "forced_offline" | "model_failure";
  engine_version: string | null;
  failed_stage: "analysis" | "validation" | "recommendation" | "lookup" | null;
  error_code: string | null;
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
    | "run.fallback"
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
  execution?: ExecutionInfo | null;
}

export interface LookupAnswer {
  question: string;
  answer: string;
  citations: Citation[];
  support: SupportState;
  snapshot_id: string;
  confidence?: Confidence | null;
  execution?: ExecutionInfo | null;
}

export interface ApiError {
  code: string;
  message: string;
  request_id: string;
  retryable: boolean;
}
