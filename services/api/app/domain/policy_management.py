"""Policy administration contracts; no generated policy semantics."""

from datetime import date, datetime
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from app.domain.contracts import ClauseKind, Contract, PolicyVersion

Id = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Label = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,31}$")]
Relation = Literal["references", "excepts", "overrides"]


class UploadPolicyInput(Contract):
    policy_id: Id | None = None
    title: Text | None = None
    category: Text | None = None
    business_area: Text | None = None
    owner: Text | None = None
    label: Label
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def valid_metadata(self) -> Self:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("The end date must be on or after the start date.")
        if self.policy_id is None and not all(
            (self.title, self.category, self.business_area, self.owner)
        ):
            raise ValueError("A new policy needs a title, category, business area and owner.")
        return self


class ClauseReview(Contract):
    kind: ClauseKind
    candidate: bool

    @model_validator(mode="after")
    def consistent_kind(self) -> Self:
        if self.kind == ClauseKind.DEFINITION and self.candidate:
            raise ValueError("Definitions are context, not requirement candidates.")
        if self.kind in (ClauseKind.REQUIREMENT, ClauseKind.EXCEPTION) and not self.candidate:
            raise ValueError("Requirements and exceptions must remain candidates.")
        return self


class RelationReview(Contract):
    source_clause_id: Id
    target_clause_id: Id
    relation: Relation
    approved: bool = False
    rationale: str = Field(default="", max_length=1000)


class StoredRelation(RelationReview):
    id: str
    source_heading: str
    target_heading: str
    target_version_id: str
    provenance: str


class DraftReviewInput(Contract):
    label: Label
    effective_from: date
    effective_to: date | None = None
    expected_revision: int = Field(ge=0)
    clauses: dict[Id, ClauseReview] = Field(max_length=1000)
    relations: list[RelationReview] = Field(default_factory=list, max_length=500)
    review_confirmed: bool = False
    acknowledge_warnings: bool = False

    @model_validator(mode="after")
    def valid_dates(self) -> Self:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("The end date must be on or after the start date.")
        return self


class DraftReview(Contract):
    version: PolicyVersion
    candidate_clause_ids: list[str]
    relations: list[StoredRelation]
    revision: int
    review_complete: bool
    warnings_acknowledged: bool
    reviewed_at: datetime | None
    source_sha256: str


class PublishInput(Contract):
    expected_revision: int = Field(ge=0)


class Publication(Contract):
    version_id: str
    snapshot_id: str
    published_at: datetime
