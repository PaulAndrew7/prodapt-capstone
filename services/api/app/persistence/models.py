"""Relational schema (IMPLEMENTATION_PLAN.md §5.1, feature F02).

Conventions:
- Text primary keys. Demo seed data uses readable IDs (`ds_v1`, `ds_v1_4_4.2`) that match
  the web fixtures; everything else gets a prefixed random ID from `new_id`.
- Enumerations are VARCHAR + CHECK constraints so migrations can extend them without
  Postgres enum-type surgery.
- Every tenant-owned root row carries `organization_id`; queries must filter on it.
- Assessment artifacts reference policy versions/clauses with RESTRICT, so a policy version
  cannot be deleted while a retained assessment cites it.
"""

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.contracts import (
    AgentRole,
    AssessmentStatus,
    ClauseKind,
    FactOrigin,
    IndexStatus,
    Likelihood,
    PolicyVersionStatus,
    RecommendationKind,
    RequirementStatus,
    ReviewState,
    Role,
    RunState,
    Severity,
    SupportState,
)

EMBEDDING_DIMENSION = 384

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def enum_col[E: StrEnum](enum: type[E], name: str) -> Enum:
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {dict[str, Any]: JSONB, list[Any]: JSONB}  # noqa: RUF012


def created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# --- Local enumerations (not part of the public contract) --------------------------------


class RequirementModality(StrEnum):
    MUST = "must"
    MUST_NOT = "must_not"
    MAY = "may"


class ReviewedState(StrEnum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    REJECTED = "rejected"


class RelationKind(StrEnum):
    REFERENCES = "references"
    EXCEPTS = "excepts"
    OVERRIDES = "overrides"


class ExtractionQuality(StrEnum):
    OK = "ok"
    WARNING = "warning"
    LOW = "low"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ReviewDisposition(StrEnum):
    ACCEPTED = "accepted"
    CHALLENGED = "challenged"
    INFORMATION_REQUESTED = "information_requested"


# --- Identity -----------------------------------------------------------------------------


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class Membership(Base):
    __tablename__ = "memberships"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[Role] = mapped_column(enum_col(Role, "role"))
    created_at: Mapped[datetime] = created_at()


# --- Policies, versions and evidence --------------------------------------------------------


class Upload(Base):
    __tablename__ = "uploads"
    __table_args__ = (UniqueConstraint("organization_id", "sha256"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("organization_id", "slug"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    business_area: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(Text)
    applicability: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = created_at()

    versions: Mapped[list["PolicyVersion"]] = relationship(
        back_populates="policy", order_by="PolicyVersion.effective_from"
    )


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("policy_id", "label"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from", name="effective_range"
        ),
        CheckConstraint(
            "status <> 'published' OR index_status = 'ready'", name="published_is_indexed"
        ),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    policy_id: Mapped[str] = mapped_column(
        ForeignKey("policies.id", ondelete="RESTRICT"), index=True
    )
    label: Mapped[str] = mapped_column(String(32))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[PolicyVersionStatus] = mapped_column(
        enum_col(PolicyVersionStatus, "version_status"), default=PolicyVersionStatus.DRAFT
    )
    index_status: Mapped[IndexStatus] = mapped_column(
        enum_col(IndexStatus, "index_status"), default=IndexStatus.INDEXING
    )
    index_revision: Mapped[str | None] = mapped_column(Text)
    original_sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(Text)
    upload_id: Mapped[str | None] = mapped_column(ForeignKey("uploads.id", ondelete="SET NULL"))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    # Where the text came from and whether it may be processed: {"kind": "synthetic", ...}.
    provenance: Mapped[dict[str, Any]] = mapped_column(default=dict)
    extraction_warnings: Mapped[list[Any]] = mapped_column(default=list)
    ingest_error: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime] = created_at()
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    policy: Mapped[Policy] = relationship(back_populates="versions")
    clauses: Mapped[list["Clause"]] = relationship(
        back_populates="version", order_by="Clause.ordinal", passive_deletes=True
    )


class DocumentPage(Base):
    """Original extracted text per page; source spans point into `raw_text`."""

    __tablename__ = "document_pages"
    policy_version_id: Mapped[str] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="CASCADE"), primary_key=True
    )
    page_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_label: Mapped[str | None] = mapped_column(String(32))
    raw_text: Mapped[str] = mapped_column(Text)
    warnings: Mapped[list[Any]] = mapped_column(default=list)


class Clause(Base):
    __tablename__ = "clauses"
    __table_args__ = (UniqueConstraint("policy_version_id", "clause_key"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    policy_version_id: Mapped[str] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="CASCADE"), index=True
    )
    # Stable logical key across versions, e.g. "4.2".
    clause_key: Mapped[str] = mapped_column(String(64))
    section_path: Mapped[list[str]] = mapped_column(ARRAY(Text))
    # Headings for each level of section_path, e.g. ["External sharing", "Data-owner approval"].
    section_headings: Mapped[list[str]] = mapped_column(ARRAY(Text))
    heading: Mapped[str] = mapped_column(Text)
    kind: Mapped[ClauseKind] = mapped_column(enum_col(ClauseKind, "clause_kind"))
    # Exact normalized clause text. Citations quote substrings of this.
    text: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    extraction_quality: Mapped[ExtractionQuality] = mapped_column(
        enum_col(ExtractionQuality, "extraction_quality"), default=ExtractionQuality.OK
    )

    version: Mapped[PolicyVersion] = relationship(back_populates="clauses")
    spans: Mapped[list["SourceSpan"]] = relationship(
        order_by="SourceSpan.page_index", passive_deletes=True
    )


class SourceSpan(Base):
    """Where a clause's text sits in the original extraction. A clause may span pages."""

    __tablename__ = "source_spans"
    __table_args__ = (
        UniqueConstraint("clause_id", "page_index", "char_start"),
        CheckConstraint("char_end > char_start", name="nonempty"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    clause_id: Mapped[str] = mapped_column(ForeignKey("clauses.id", ondelete="CASCADE"), index=True)
    page_index: Mapped[int] = mapped_column(Integer)
    page_label: Mapped[str | None] = mapped_column(String(32))
    # Offsets into document_pages.raw_text for this page.
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    # Offsets into clauses.text covered by this span.
    text_start: Mapped[int] = mapped_column(Integer)
    text_end: Mapped[int] = mapped_column(Integer)
    # Page bounding boxes only when the parser reports them; never guessed.
    bboxes: Mapped[list[Any] | None] = mapped_column(JSONB)


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (UniqueConstraint("policy_version_id", "requirement_key"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    policy_version_id: Mapped[str] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="CASCADE"), index=True
    )
    requirement_key: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(Text)
    modality: Mapped[RequirementModality] = mapped_column(enum_col(RequirementModality, "modality"))
    trigger: Mapped[str] = mapped_column(Text)
    required_action: Mapped[str] = mapped_column(Text)
    exception_refs: Mapped[list[Any]] = mapped_column(default=list)
    evidence_needed: Mapped[list[Any]] = mapped_column(default=list)
    # Allowlisted JSON rule (§7.4); only executable once reviewed.
    rule: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    review_state: Mapped[ReviewedState] = mapped_column(
        enum_col(ReviewedState, "review_state"), default=ReviewedState.PROPOSED
    )
    created_at: Mapped[datetime] = created_at()


class RequirementClause(Base):
    __tablename__ = "requirement_clauses"
    requirement_id: Mapped[str] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), primary_key=True
    )
    clause_id: Mapped[str] = mapped_column(
        ForeignKey("clauses.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("clause_id", "ordinal"),
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    clause_id: Mapped[str] = mapped_column(ForeignKey("clauses.id", ondelete="CASCADE"), index=True)
    policy_version_id: Mapped[str] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    # "Policy title > section heading > clause heading", weighted above body text.
    prefix: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION))
    embedding_model: Mapped[str | None] = mapped_column(Text)
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', prefix), 'A') || "
            "setweight(to_tsvector('english', text), 'B')",
            persisted=True,
        ),
    )


class ClauseRelation(Base):
    __tablename__ = "clause_relations"
    __table_args__ = (UniqueConstraint("source_clause_id", "target_clause_id", "relation"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_clause_id: Mapped[str] = mapped_column(
        ForeignKey("clauses.id", ondelete="CASCADE"), index=True
    )
    target_clause_id: Mapped[str] = mapped_column(
        ForeignKey("clauses.id", ondelete="CASCADE"), index=True
    )
    relation: Mapped[RelationKind] = mapped_column(enum_col(RelationKind, "relation"))
    provenance: Mapped[str] = mapped_column(String(32), default="extracted")
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PolicySnapshot(Base):
    """Immutable set of policy versions an assessment was run against."""

    __tablename__ = "policy_snapshots"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = created_at()


class SnapshotVersion(Base):
    __tablename__ = "snapshot_versions"
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("policy_snapshots.id", ondelete="CASCADE"), primary_key=True
    )
    policy_version_id: Mapped[str] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    index_revision: Mapped[str] = mapped_column(Text)


# --- Cases and assessments --------------------------------------------------------------------


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (Index("ix_cases_org_updated", "organization_id", "updated_at"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(Text)
    business_area: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text, default="")
    as_of: Mapped[date] = mapped_column(Date)
    # Optimistic concurrency: writers send the version they read (409 on mismatch).
    lock_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ScenarioRevision(Base):
    """Immutable. A fact change creates a new revision; hypothetical branches are flagged."""

    __tablename__ = "scenario_revisions"
    __table_args__ = (UniqueConstraint("case_id", "revision_number"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    parent_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("scenario_revisions.id", ondelete="SET NULL")
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    hypothetical: Mapped[bool] = mapped_column(Boolean, default=False)
    changed_facts: Mapped[list[Any]] = mapped_column(default=list)
    confirmed_assumptions: Mapped[list[Any]] = mapped_column(default=list)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = created_at()


class CaseMessage(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    scenario_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("scenario_revisions.id", ondelete="SET NULL")
    )
    role: Mapped[str] = mapped_column(
        String(16), CheckConstraint("role IN ('user', 'assistant')", name="role")
    )
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class Fact(Base):
    __tablename__ = "facts"
    __table_args__ = (
        UniqueConstraint("scenario_revision_id", "key"),
        # Unknown means no value; a value is never silently treated as unknown.
        CheckConstraint("(origin = 'unknown') = (value IS NULL)", name="unknown_has_no_value"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    scenario_revision_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_revisions.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(128))
    label: Mapped[str] = mapped_column(Text)
    value: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(32))
    origin: Mapped[FactOrigin] = mapped_column(enum_col(FactOrigin, "origin"))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    source_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )


class AssessmentRun(Base):
    __tablename__ = "assessment_runs"
    __table_args__ = (
        UniqueConstraint("case_id", "idempotency_key"),
        Index("ix_assessment_runs_org_created", "organization_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    scenario_revision_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_revisions.id", ondelete="RESTRICT")
    )
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("policy_snapshots.id", ondelete="RESTRICT"), index=True
    )
    state: Mapped[RunState] = mapped_column(
        enum_col(RunState, "run_state"), default=RunState.QUEUED
    )
    result_status: Mapped[AssessmentStatus | None] = mapped_column(
        enum_col(AssessmentStatus, "result_status")
    )
    review_state: Mapped[ReviewState] = mapped_column(
        enum_col(ReviewState, "review_state"), default=ReviewState.UNREVIEWED
    )
    idempotency_key: Mapped[str] = mapped_column(String(128))
    # Model, prompt and retrieval configuration versions used by this run.
    config: Mapped[dict[str, Any]] = mapped_column(default=dict)
    budget: Mapped[dict[str, Any]] = mapped_column(default=dict)
    usage: Mapped[dict[str, Any]] = mapped_column(default=dict)
    # Final assessment document; written once when the run completes.
    assessment: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    trace_id: Mapped[str | None] = mapped_column(String(64))
    # Fencing token: a stale worker cannot write after another worker takes the run over.
    lock_version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = created_at()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Citation(Base):
    __tablename__ = "citations"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True
    )
    policy_version_id: Mapped[str] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="RESTRICT")
    )
    clause_id: Mapped[str] = mapped_column(
        ForeignKey("clauses.id", ondelete="RESTRICT"), index=True
    )
    span_id: Mapped[str | None] = mapped_column(ForeignKey("source_spans.id", ondelete="RESTRICT"))
    page_index: Mapped[int] = mapped_column(Integer)
    section_path: Mapped[list[str]] = mapped_column(ARRAY(Text))
    quote: Mapped[str] = mapped_column(Text)
    quote_sha256: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(Text)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[str | None] = mapped_column(
        ForeignKey("requirements.id", ondelete="RESTRICT")
    )
    requirement_ref: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[RequirementStatus] = mapped_column(
        enum_col(RequirementStatus, "requirement_status")
    )
    support: Mapped[SupportState] = mapped_column(enum_col(SupportState, "support"))
    rationale: Mapped[str] = mapped_column(Text)
    missing_facts: Mapped[list[Any]] = mapped_column(default=list)


class FindingFact(Base):
    __tablename__ = "finding_facts"
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True
    )
    fact_id: Mapped[str] = mapped_column(
        ForeignKey("facts.id", ondelete="RESTRICT"), primary_key=True, index=True
    )


class FindingCitation(Base):
    __tablename__ = "finding_citations"
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True
    )
    citation_id: Mapped[str] = mapped_column(
        ForeignKey("citations.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Risk(Base):
    __tablename__ = "risks"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True
    )
    severity: Mapped[Severity] = mapped_column(enum_col(Severity, "severity"))
    likelihood: Mapped[Likelihood] = mapped_column(enum_col(Likelihood, "likelihood"))
    description: Mapped[str] = mapped_column(Text)
    rubric_version: Mapped[str] = mapped_column(String(64))


class RiskFinding(Base):
    __tablename__ = "risk_findings"
    risk_id: Mapped[str] = mapped_column(
        ForeignKey("risks.id", ondelete="CASCADE"), primary_key=True
    )
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(Text)
    suggested_role: Mapped[str] = mapped_column(Text)
    completion_criteria: Mapped[str] = mapped_column(Text)
    kind: Mapped[RecommendationKind] = mapped_column(
        enum_col(RecommendationKind, "recommendation_kind")
    )


class RecommendationFinding(Base):
    __tablename__ = "recommendation_findings"
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), primary_key=True
    )
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class RecommendationCitation(Base):
    __tablename__ = "recommendation_citations"
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), primary_key=True
    )
    citation_id: Mapped[str] = mapped_column(
        ForeignKey("citations.id", ondelete="CASCADE"), primary_key=True, index=True
    )


# --- Workflow trace, review, jobs and audit ---------------------------------------------------


class RunEventRow(Base):
    """Append-only public event log; `sequence` is gap-free per run."""

    __tablename__ = "run_events"
    __table_args__ = (UniqueConstraint("run_id", "sequence"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("assessment_runs.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(8), default="1.0")
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    occurred_at: Mapped[datetime] = created_at()


class AgentMessageRow(Base):
    __tablename__ = "agent_messages"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True
    )
    sender: Mapped[AgentRole] = mapped_column(enum_col(AgentRole, "sender"))
    # An agent role or "gate" (the final evidence gate).
    recipient: Mapped[str] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    causal_parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_messages.id", ondelete="CASCADE")
    )
    remaining_repair_rounds: Mapped[int] = mapped_column(Integer, default=0)
    schema_version: Mapped[str] = mapped_column(String(8), default="1.0")
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = created_at()


class Review(Base):
    """Immutable reviewer disposition; never overwrites model findings."""

    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True
    )
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    disposition: Mapped[ReviewDisposition] = mapped_column(
        enum_col(ReviewDisposition, "disposition")
    )
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class Job(Base):
    """Durable work item claimed with a lease (plan §15.1)."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("job_type", "idempotency_key"),
        Index("ix_jobs_claim", "state", "next_attempt_at"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    job_type: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    state: Mapped[JobState] = mapped_column(
        enum_col(JobState, "job_state"), default=JobState.QUEUED
    )
    progress: Mapped[dict[str, Any]] = mapped_column(default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    lease_owner: Mapped[str | None] = mapped_column(Text)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime] = created_at()
    error_category: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditEvent(Base):
    """Append-only (enforced by trigger). Targets are not foreign keys, so the record of an
    action survives deletion of the object it describes; it holds metadata, not content."""

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_org_time", "organization_id", "occurred_at"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    actor_id: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str] = mapped_column(Text)
    changed_fields: Mapped[dict[str, Any]] = mapped_column(default=dict)
    request_id: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = created_at()
