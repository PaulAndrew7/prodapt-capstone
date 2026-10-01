"""Admin PDF intake, source review and atomic snapshot publication."""

import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentPrincipal, DbSession, Principal
from app.api.errors import AppError, not_found
from app.api.policies import get_version
from app.config import get_settings
from app.domain.contracts import ClauseKind, IndexStatus, PolicyVersionStatus
from app.domain.policy_management import (
    DraftReview,
    DraftReviewInput,
    Publication,
    PublishInput,
    StoredRelation,
    UploadPolicyInput,
)
from app.ingestion.pdf import IngestionError
from app.ingestion.pipeline import VersionInput, ingest_version
from app.ingestion.review_metadata import reviewed_candidates
from app.persistence import models as m
from app.retrieval.embeddings import get_embedder
from app.storage import get_storage

router = APIRouter(prefix="/api/v1/admin", tags=["policy management"])


def admin(principal: Principal) -> None:
    if not principal.is_admin:
        raise AppError(403, "admin_required", "Only an organization admin can manage policies.")


def version_for(session: DbSession, principal: Principal, version_id: str) -> m.PolicyVersion:
    version = session.scalar(
        select(m.PolicyVersion)
        .join(m.Policy)
        .where(
            m.PolicyVersion.id == version_id,
            m.Policy.organization_id == principal.organization_id,
        )
        .with_for_update(of=m.PolicyVersion)
    )
    if version is None:
        raise not_found("Policy version")
    return version


def audit(session: DbSession, principal: Principal, action: str, version_id: str) -> None:
    session.add(
        m.AuditEvent(
            id=m.new_id("audit"),
            organization_id=principal.organization_id,
            actor_id=principal.user_id,
            action=action,
            target_type="policy_version",
            target_id=version_id,
            changed_fields={"version_id": version_id},
        )
    )


def review_view(session: DbSession, principal: Principal, v: m.PolicyVersion) -> DraftReview:
    candidates = reviewed_candidates(v.id, v.provenance)
    relations = session.scalars(
        select(m.ClauseRelation)
        .where(m.ClauseRelation.source_clause_id.in_([c.id for c in v.clauses]))
        .order_by(m.ClauseRelation.id)
    )
    details = []
    rationales = v.provenance.get("relation_rationales", {})
    for r in relations:
        source = session.get_one(m.Clause, r.source_clause_id)
        target = session.get_one(m.Clause, r.target_clause_id)
        if target.version.policy.organization_id != principal.organization_id:
            continue
        details.append(
            StoredRelation(
                id=r.id,
                source_clause_id=source.id,
                target_clause_id=target.id,
                relation=r.relation.value,
                approved=r.approved_by is not None,
                rationale=rationales.get(r.id, ""),
                source_heading=source.heading,
                target_heading=target.heading,
                target_version_id=target.policy_version_id,
                provenance=r.provenance,
            )
        )
    return DraftReview(
        version=get_version(v.id, session, principal),
        candidate_clause_ids=[
            c.id
            for c in v.clauses
            if c.kind in (ClauseKind.REQUIREMENT, ClauseKind.EXCEPTION)
            or (c.kind != ClauseKind.DEFINITION and c.clause_key in candidates)
        ],
        relations=details,
        revision=v.provenance.get("review_revision", 0),
        review_complete=bool(v.provenance.get("review_complete")),
        warnings_acknowledged=bool(v.provenance.get("warnings_acknowledged")),
        reviewed_at=v.provenance.get("reviewed_at"),
        source_sha256=v.original_sha256,
    )


@router.post("/policies/upload", response_model=DraftReview, status_code=201)
def upload_policy(
    session: DbSession,
    principal: CurrentPrincipal,
    metadata: Annotated[str, Form(max_length=4000)],
    file: Annotated[UploadFile, File()],
) -> DraftReview:
    admin(principal)
    try:
        spec = UploadPolicyInput.model_validate_json(metadata)
    except ValidationError as exc:
        raise AppError(
            422, "invalid_metadata", "Check the policy fields, dates and version label."
        ) from exc
    data = file.file.read(get_settings().max_upload_bytes + 1)
    if len(data) > get_settings().max_upload_bytes:
        raise AppError(413, "file_too_large", "The PDF exceeds the configured upload limit.")
    # Serialize intake with publication; duplicate labels cannot race within an organization.
    session.scalar(
        select(m.Organization)
        .where(m.Organization.id == principal.organization_id)
        .with_for_update()
    )
    policy = session.get(m.Policy, spec.policy_id) if spec.policy_id else None
    if spec.policy_id and (policy is None or policy.organization_id != principal.organization_id):
        raise not_found("Policy")
    if policy is None:
        pid = m.new_id("policy")
        policy = m.Policy(
            id=pid,
            organization_id=principal.organization_id,
            slug=pid,
            title=spec.title,
            category=spec.category,
            business_area=spec.business_area,
            owner=spec.owner,
        )
        session.add(policy)
        session.flush()
    if session.scalar(
        select(m.PolicyVersion.id).where(
            m.PolicyVersion.policy_id == policy.id, m.PolicyVersion.label == spec.label
        )
    ):
        raise AppError(
            409, "version_conflict", "That version label already exists. Choose a new label."
        )
    try:
        result = ingest_version(
            session,
            data,
            VersionInput(
                policy=policy,
                version_id=m.new_id("version"),
                label=spec.label,
                effective_from=spec.effective_from,
                effective_to=spec.effective_to,
                status=PolicyVersionStatus.DRAFT,
                provenance={
                    "kind": "admin_upload",
                    "managed_upload": True,
                    "reviewed_candidates": [],
                    "review_revision": 0,
                },
            ),
            storage=get_storage(),
            embedder=get_embedder(),
        )
        sha = hashlib.sha256(data).hexdigest()
        upload = session.scalar(
            select(m.Upload).where(
                m.Upload.organization_id == principal.organization_id, m.Upload.sha256 == sha
            )
        )
        if upload is None:
            upload = m.Upload(
                id=m.new_id("upload"),
                organization_id=principal.organization_id,
                uploaded_by=principal.user_id,
                filename=(file.filename or "policy.pdf").replace("\\", "/").split("/")[-1][:200],
                content_type="application/pdf",
                size_bytes=len(data),
                sha256=sha,
                storage_key=result.version.storage_key,
            )
            session.add(upload)
            session.flush()
        result.version.upload_id = upload.id
        audit(session, principal, "policy.uploaded", result.version.id)
        session.commit()
    except IngestionError as exc:
        session.rollback()
        raise AppError(422, exc.category, exc.message) from exc
    except IntegrityError as exc:
        session.rollback()
        raise AppError(
            409, "version_conflict", "The policy changed. Reload and try again."
        ) from exc
    return review_view(session, principal, result.version)


@router.get("/policy-versions/{version_id}/review", response_model=DraftReview)
def get_review(version_id: str, session: DbSession, principal: CurrentPrincipal) -> DraftReview:
    admin(principal)
    return review_view(session, principal, version_for(session, principal, version_id))


@router.post("/policy-versions/{version_id}/review", response_model=DraftReview)
def save_review(
    version_id: str,
    body: DraftReviewInput,
    session: DbSession,
    principal: CurrentPrincipal,
) -> DraftReview:
    admin(principal)
    session.scalar(
        select(m.Organization)
        .where(m.Organization.id == principal.organization_id)
        .with_for_update()
    )
    v = version_for(session, principal, version_id)
    if v.status != PolicyVersionStatus.DRAFT:
        raise AppError(409, "published_immutable", "Published policy versions cannot be edited.")
    revision = v.provenance.get("review_revision", 0)
    if body.expected_revision != revision:
        raise AppError(409, "stale_review", "This draft was changed. Reload before saving.")
    clauses = {c.id: c for c in v.clauses}
    if set(body.clauses) != set(clauses):
        raise AppError(422, "incomplete_review", "Review every extracted clause in this draft.")
    if session.scalar(
        select(m.PolicyVersion.id).where(
            m.PolicyVersion.policy_id == v.policy_id,
            m.PolicyVersion.label == body.label,
            m.PolicyVersion.id != v.id,
        )
    ):
        raise AppError(409, "version_conflict", "That version label already exists.")
    seen = set()
    for item in body.relations:
        identity = (item.source_clause_id, item.target_clause_id, item.relation)
        if item.source_clause_id not in clauses or identity in seen or identity[0] == identity[1]:
            raise AppError(
                422, "invalid_relation", "A relationship needs distinct, valid clause endpoints."
            )
        seen.add(identity)
        target = session.get(m.Clause, item.target_clause_id)
        if target is None or target.version.policy.organization_id != principal.organization_id:
            raise not_found("Target clause")
        if target.policy_version_id != v.id and target.version.status == PolicyVersionStatus.DRAFT:
            raise AppError(
                422, "draft_target", "Cross-policy relationships must target published clauses."
            )
        if item.approved and item.relation != "references" and not item.rationale.strip():
            raise AppError(
                422, "relation_rationale", "Explain each approved exception or override."
            )
    v.label, v.effective_from, v.effective_to = body.label, body.effective_from, body.effective_to
    for cid, clause_review in body.clauses.items():
        clauses[cid].kind = clause_review.kind
    session.execute(delete(m.ClauseRelation).where(m.ClauseRelation.source_clause_id.in_(clauses)))
    now = datetime.now(UTC)
    rationales = {}
    for item in body.relations:
        rid = m.new_id("relation")
        rationales[rid] = item.rationale.strip()
        session.add(
            m.ClauseRelation(
                id=rid,
                source_clause_id=item.source_clause_id,
                target_clause_id=item.target_clause_id,
                relation=m.RelationKind(item.relation),
                provenance="admin_review",
                approved_by=principal.user_id if item.approved else None,
                approved_at=now if item.approved else None,
            )
        )
    v.provenance = {
        **v.provenance,
        "managed_upload": True,
        "review_revision": revision + 1,
        "review_complete": body.review_confirmed,
        "reviewed_by": principal.user_id,
        "reviewed_at": now.isoformat(),
        "warnings_acknowledged": body.acknowledge_warnings,
        "reviewed_candidates": [
            clauses[cid].clause_key for cid, item in body.clauses.items() if item.candidate
        ],
        "relation_rationales": rationales,
    }
    audit(session, principal, "policy.reviewed", v.id)
    session.commit()
    return review_view(session, principal, v)


@router.post("/policy-versions/{version_id}/publish", response_model=Publication)
def publish_policy(
    version_id: str,
    body: PublishInput,
    session: DbSession,
    principal: CurrentPrincipal,
) -> Publication:
    admin(principal)
    # Always lock organization before version, matching upload/publication lock order.
    session.scalar(
        select(m.Organization)
        .where(m.Organization.id == principal.organization_id)
        .with_for_update()
    )
    v = version_for(session, principal, version_id)
    existing = v.provenance.get("published_snapshot_id")
    if existing and v.published_at:
        return Publication(
            version_id=v.id, snapshot_id=existing, published_at=v.published_at.astimezone(UTC)
        )
    if v.status != PolicyVersionStatus.DRAFT:
        raise AppError(409, "published_immutable", "This version is already published.")
    if body.expected_revision != v.provenance.get("review_revision", 0):
        raise AppError(409, "stale_review", "This draft was changed. Reload before publishing.")
    if v.index_status != IndexStatus.READY or not v.provenance.get("review_complete"):
        raise AppError(
            422, "review_required", "Ready indexes and a complete clause review are required."
        )
    if v.extraction_warnings and not v.provenance.get("warnings_acknowledged"):
        raise AppError(
            422, "warnings_unacknowledged", "Review and acknowledge the extraction warnings."
        )
    if not get_storage().path_for(v.storage_key).is_file():
        raise AppError(410, "source_missing", "Restore the original PDF before publishing.")
    if session.scalar(
        select(m.PolicyVersion.id).where(
            m.PolicyVersion.policy_id == v.policy_id,
            m.PolicyVersion.id != v.id,
            m.PolicyVersion.status != PolicyVersionStatus.DRAFT,
            m.PolicyVersion.effective_from == v.effective_from,
        )
    ):
        raise AppError(
            409,
            "ambiguous_effective_date",
            "Another version starts on that date. Choose a distinct start date.",
        )
    now = datetime.now(UTC)
    v.status, v.published_at = PolicyVersionStatus.PUBLISHED, now
    snapshot_id = m.new_id("snapshot")
    v.provenance = {**v.provenance, "published_snapshot_id": snapshot_id}
    session.add(
        m.PolicySnapshot(
            id=snapshot_id,
            organization_id=principal.organization_id,
            description=f"Published {v.policy.title} {v.label}",
            created_at=now,
        )
    )
    session.flush()
    versions = session.scalars(
        select(m.PolicyVersion)
        .join(m.Policy)
        .where(
            m.Policy.organization_id == principal.organization_id,
            m.PolicyVersion.status != PolicyVersionStatus.DRAFT,
            m.PolicyVersion.index_status == IndexStatus.READY,
        )
    )
    session.add_all(
        m.SnapshotVersion(
            snapshot_id=snapshot_id,
            policy_version_id=row.id,
            index_revision=row.index_revision or "",
        )
        for row in versions
    )
    audit(session, principal, "policy.published", v.id)
    session.commit()
    return Publication(version_id=v.id, snapshot_id=snapshot_id, published_at=now)
