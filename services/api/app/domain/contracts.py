"""Public API contracts (IMPLEMENTATION_PLAN.md §5).

Field names match `apps/web/src/lib/api/types.ts` exactly so the web client can swap its
hand-written mirror for types generated from the exported OpenAPI document. Change a
contract here first, bump `SCHEMA_VERSION` for breaking changes, and update the shared
fixture in `packages/contracts/fixtures/`.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal["1.0"] = "1.0"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# --- Result semantics (§5.2) -------------------------------------------------------------


class AssessmentStatus(StrEnum):
    """Displayed result, chosen by the ordered rules in §5.2 (first match wins)."""

    NON_COMPLIANT = "non_compliant"
    CONFLICTING_POLICY = "conflicting_policy"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    COMPLIANT_WITHIN_SCOPE = "compliant_within_scope"
    OUT_OF_SCOPE = "out_of_scope"


class RequirementStatus(StrEnum):
    MET = "met"
    VIOLATED = "violated"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    CONFLICT = "conflict"


class SupportState(StrEnum):
    VALIDATED = "validated"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    PENDING = "pending"


class FactOrigin(StrEnum):
    """An absent fact stays `unknown`; it never becomes a negative assertion."""

    PROVIDED = "provided"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class RunState(StrEnum):
    """Workflow state. A timeout is `failed`, never a compliance verdict."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class AgentRole(StrEnum):
    RETRIEVAL = "retrieval"
    ANALYSIS = "analysis"
    RISK = "risk"
    VALIDATION = "validation"
    RECOMMENDATION = "recommendation"


class ReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    ACCEPTED = "accepted"
    CHALLENGED = "challenged"
    INFORMATION_REQUESTED = "information_requested"


class PolicyVersionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"


class IndexStatus(StrEnum):
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class ClauseKind(StrEnum):
    DEFINITION = "definition"
    REQUIREMENT = "requirement"
    EXCEPTION = "exception"
    GENERAL = "general"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Likelihood(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationKind(StrEnum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"


class Role(StrEnum):
    REQUESTER = "requester"
    REVIEWER = "reviewer"
    ADMIN = "admin"


# --- Policies and evidence ----------------------------------------------------------------


class PolicyVersionSummary(Contract):
    id: str
    label: str
    effective_from: date
    effective_to: date | None
    status: PolicyVersionStatus
    index_status: IndexStatus
    pages: int


class Policy(Contract):
    id: str
    title: str
    category: str
    business_area: str
    owner: str
    active_version_id: str | None
    versions: list[PolicyVersionSummary]


class Clause(Contract):
    id: str
    policy_id: str
    policy_version_id: str
    section_path: list[str]
    heading: str
    text: str
    page_index: int = Field(description="Zero-based index of the page where the clause starts.")
    kind: ClauseKind


class PolicyVersion(PolicyVersionSummary):
    policy_id: str
    policy_title: str
    clauses: list[Clause]
    extraction_warnings: list[str]


class Citation(Contract):
    """Built by the backend from stored clause records; models only select allowed IDs."""

    id: str
    policy_version_id: str
    clause_id: str
    page_index: int
    section_path: list[str]
    quote: str
    source_url: str


# --- Cases and assessments ----------------------------------------------------------------


class Fact(Contract):
    id: str
    key: str
    label: str
    value: str | None
    origin: FactOrigin
    confirmed: bool
    source_message_id: str | None = None


class Finding(Contract):
    id: str
    requirement_id: str
    title: str
    status: RequirementStatus
    rationale: str
    fact_ids: list[str]
    citation_ids: list[str]
    support: SupportState
    missing_facts: list[str]


class Risk(Contract):
    id: str
    finding_ids: list[str]
    severity: Severity
    likelihood: Likelihood
    description: str
    rubric_version: str


class Recommendation(Contract):
    id: str
    finding_ids: list[str]
    citation_ids: list[str]
    action: str
    suggested_role: str
    completion_criteria: str
    kind: RecommendationKind


class Assessment(Contract):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    run_id: str
    case_revision_id: str
    policy_snapshot_id: str
    as_of: date
    status: AssessmentStatus
    scope: str
    summary: str
    findings: list[Finding]
    citations: list[Citation]
    risks: list[Risk]
    recommendations: list[Recommendation]
    limitations: list[str]
    review_state: ReviewState
    hypothetical: bool | None = None


class ClarificationQuestion(Contract):
    id: str
    question: str
    reason: str
    clause_ref: str
    fact_key: str
    answer_kind: Literal["choice", "text"]
    choices: list[str] | None = None


class Message(Contract):
    id: str
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime


# --- Events and agent exchanges (§5.5) ---------------------------------------------------


class EventType(StrEnum):
    RUN_QUEUED = "run.queued"
    RUN_STARTED = "run.started"
    RETRIEVAL_COMPLETED = "retrieval.completed"
    ANALYSIS_COMPLETED = "analysis.completed"
    RISK_COMPLETED = "risk.completed"
    VALIDATION_COMPLETED = "validation.completed"
    RECOMMENDATION_COMPLETED = "recommendation.completed"
    CLARIFICATION_REQUIRED = "clarification.required"
    RUN_RESUMED = "run.resumed"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELED = "run.canceled"


class RunEvent(Contract):
    """Public SSE envelope. Clients deduplicate by `event_id` and replay by `sequence`."""

    event_id: str
    run_id: str
    sequence: int = Field(ge=1)
    occurred_at: datetime
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    type: EventType
    payload: dict[str, Any]


class AgentMessage(Contract):
    """Public, sanitized view of one agent-to-agent exchange for the trace UI."""

    message_id: str
    sender: AgentRole
    recipient: AgentRole | Literal["gate"]
    type: str
    summary: str
    causal_parent_id: str | None
    at_ms: int


class AgentExchange(Contract):
    """Internal typed A2A message between runtime agents (not the external A2A protocol)."""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    message_id: str
    run_id: str
    sender: AgentRole
    recipient: AgentRole | Literal["gate"]
    type: str
    causal_parent_id: str | None
    payload: dict[str, Any]
    remaining_repair_rounds: int = Field(ge=0)


class CaseSummary(Contract):
    id: str
    title: str
    owner: str
    business_area: str
    status: AssessmentStatus | None
    run_state: RunState | None
    unresolved_facts: int
    review_state: ReviewState
    updated_at: datetime


class CaseDetail(CaseSummary):
    as_of: date
    scope: str
    scenario_text: str
    policy_snapshot_id: str
    messages: list[Message]
    facts: list[Fact]
    latest_run_id: str | None
    assessment: Assessment | None
    pending_questions: list[ClarificationQuestion]
    agent_messages: list[AgentMessage]


# --- Search and lookup --------------------------------------------------------------------


class SearchRequest(Contract):
    question: str = Field(min_length=2, max_length=2000)
    policy_ids: list[str] | None = Field(
        default=None, description="Explicit user-selected scope. Omit to search every policy."
    )
    as_of: date | None = Field(default=None, description="Selects versions in effect on a date.")
    limit: int = Field(default=10, ge=1, le=50)


class SearchHit(Contract):
    clause: Clause
    policy_title: str
    version_label: str
    chunk_id: str
    score: float = Field(description="Rank-fusion score. A ranking heuristic, not a probability.")
    lexical_rank: int | None
    dense_rank: int | None
    citation: Citation


class SearchResponse(Contract):
    question: str
    policy_snapshot_id: str | None
    hits: list[SearchHit]
    channels: list[Literal["lexical", "dense"]]
    latency_ms: int


class LookupAnswer(Contract):
    question: str
    answer: str
    citations: list[Citation]
    support: SupportState
    snapshot_id: str


class Page[T](Contract):
    items: list[T]
    next_cursor: str | None = None


class ApiError(Contract):
    code: str
    message: str
    request_id: str
    retryable: bool
    details: list[dict[str, Any]] | None = None


class HealthStatus(Contract):
    status: Literal["ok", "degraded", "unavailable"]
    checks: dict[str, str]
