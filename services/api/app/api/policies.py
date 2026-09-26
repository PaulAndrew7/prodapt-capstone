"""Policy library, versions, clauses and original documents (F04 backend slice)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.citations import clause_contract
from app.api.deps import CurrentPrincipal, DbSession, Principal
from app.api.errors import AppError, not_found
from app.domain.contracts import (
    Clause,
    Contract,
    Page,
    Policy,
    PolicyVersion,
    PolicyVersionStatus,
    PolicyVersionSummary,
)
from app.persistence import models as m
from app.storage import get_storage

router = APIRouter(prefix="/api/v1", tags=["policies"])


class SourceSpan(Contract):
    page_index: int
    page_label: str | None
    char_start: int = Field(description="Offset into the page's extracted text.")
    char_end: int
    text_start: int = Field(description="Offset into the clause text.")
    text_end: int


class ClauseWithSource(Clause):
    clause_key: str
    section_headings: list[str]
    page_end: int
    extraction_quality: str
    spans: list[SourceSpan]


class PageText(Contract):
    policy_version_id: str
    page_index: int
    page_label: str | None
    text: str
    warnings: list[str]
    spans: list[dict[str, str | int]] = Field(
        description="Clause spans on this page: clause_id, char_start, char_end."
    )


def _today() -> date:
    return date.today()


def _visible(version: m.PolicyVersion, principal: Principal) -> bool:
    return version.status != PolicyVersionStatus.DRAFT or principal.role != "requester"


def _summary(v: m.PolicyVersion) -> PolicyVersionSummary:
    return PolicyVersionSummary(
        id=v.id,
        label=v.label,
        effective_from=v.effective_from,
        effective_to=v.effective_to,
        status=v.status,
        index_status=v.index_status,
        pages=v.page_count,
    )


def _active_version_id(versions: list[m.PolicyVersion], today: date) -> str | None:
    live = [v for v in versions if v.status == PolicyVersionStatus.PUBLISHED]
    in_effect = [
        v
        for v in live
        if v.effective_from <= today and (v.effective_to is None or v.effective_to >= today)
    ]
    pick = max(in_effect or live, key=lambda v: v.effective_from, default=None)
    return pick.id if pick else None


def _version_for(session: DbSession, principal: Principal, version_id: str) -> m.PolicyVersion:
    version = session.scalar(
        select(m.PolicyVersion)
        .join(m.Policy)
        .where(
            m.PolicyVersion.id == version_id, m.Policy.organization_id == principal.organization_id
        )
    )
    if version is None or not _visible(version, principal):
        raise not_found("Policy version")
    return version


@router.get("/policies", response_model=Page[Policy])
def list_policies(session: DbSession, principal: CurrentPrincipal) -> Page[Policy]:
    rows = session.scalars(
        select(m.Policy)
        .where(m.Policy.organization_id == principal.organization_id)
        .options(selectinload(m.Policy.versions))
        .order_by(m.Policy.title)
    )
    today = _today()
    items = []
    for p in rows:
        versions = [v for v in p.versions if _visible(v, principal)]
        items.append(
            Policy(
                id=p.id,
                title=p.title,
                category=p.category,
                business_area=p.business_area,
                owner=p.owner,
                active_version_id=_active_version_id(versions, today),
                versions=[_summary(v) for v in versions],
            )
        )
    return Page[Policy](items=items)


@router.get("/policies/{policy_id}/versions", response_model=list[PolicyVersionSummary])
def list_versions(
    policy_id: str, session: DbSession, principal: CurrentPrincipal
) -> list[PolicyVersionSummary]:
    policy = session.get(m.Policy, policy_id)
    if policy is None or policy.organization_id != principal.organization_id:
        raise not_found("Policy")
    return [_summary(v) for v in policy.versions if _visible(v, principal)]


@router.get("/policy-versions/{version_id}", response_model=PolicyVersion)
def get_version(version_id: str, session: DbSession, principal: CurrentPrincipal) -> PolicyVersion:
    v = _version_for(session, principal, version_id)
    return PolicyVersion(
        **_summary(v).model_dump(),
        policy_id=v.policy_id,
        policy_title=v.policy.title,
        clauses=[clause_contract(c) for c in v.clauses],
        extraction_warnings=list(v.extraction_warnings),
    )


@router.get("/policy-versions/{version_id}/clauses", response_model=list[ClauseWithSource])
def list_clauses(
    version_id: str, session: DbSession, principal: CurrentPrincipal
) -> list[ClauseWithSource]:
    v = _version_for(session, principal, version_id)
    return [
        ClauseWithSource(
            **clause_contract(c).model_dump(),
            clause_key=c.clause_key,
            section_headings=list(c.section_headings),
            page_end=c.page_end,
            extraction_quality=c.extraction_quality.value,
            spans=[SourceSpan.model_validate(s) for s in c.spans],
        )
        for c in v.clauses
    ]


@router.get("/policy-versions/{version_id}/pages/{page_index}", response_model=PageText)
def get_page_text(
    version_id: str, page_index: int, session: DbSession, principal: CurrentPrincipal
) -> PageText:
    v = _version_for(session, principal, version_id)
    page = session.get(m.DocumentPage, (v.id, page_index))
    if page is None:
        raise not_found("Page")
    spans = session.scalars(
        select(m.SourceSpan)
        .join(m.Clause)
        .where(m.Clause.policy_version_id == v.id, m.SourceSpan.page_index == page_index)
        .order_by(m.SourceSpan.char_start)
    )
    return PageText(
        policy_version_id=v.id,
        page_index=page.page_index,
        page_label=page.page_label,
        text=page.raw_text,
        warnings=list(page.warnings),
        spans=[
            {"clause_id": s.clause_id, "char_start": s.char_start, "char_end": s.char_end}
            for s in spans
        ],
    )


@router.get(
    "/policy-versions/{version_id}/source",
    response_class=FileResponse,
    responses={200: {"content": {"application/pdf": {}}}, 307: {"description": "Page anchor"}},
)
def get_source(
    version_id: str,
    session: DbSession,
    principal: CurrentPrincipal,
    page: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    """The authorized original PDF. `?page=N` redirects to `#page=N` for browser viewers."""
    v = _version_for(session, principal, version_id)
    if page is not None:
        if page > v.page_count:
            raise AppError(422, "page_out_of_range", f"This document has {v.page_count} pages.")
        return RedirectResponse(f"/api/v1/policy-versions/{v.id}/source#page={page}", 307)
    path = get_storage().path_for(v.storage_key)
    if not path.is_file():
        raise AppError(
            410, "source_missing", "The original document is missing from storage.", retryable=False
        )
    filename = f"{v.policy_id}_{v.label}.pdf"
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )
