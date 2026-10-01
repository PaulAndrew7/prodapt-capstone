"""Retrieval stage (plan §6.2, §7.1): no model call.

Runs the existing hybrid search against the run's snapshot and date, then adds the clauses
needed to read each hit: clauses it cites, exception clauses that carve it out, and the
definitions in the same policy version. The bundle is capped so model input stays bounded.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.contracts import ClauseKind, SearchRequest
from app.ingestion.review_metadata import reviewed_candidates
from app.persistence import models as m
from app.retrieval.embeddings import Embedder
from app.retrieval.search import eligible_version_ids, search

SEARCH_LIMIT = 10
MAX_CLAUSES = 14


@dataclass(frozen=True)
class EvidenceClause:
    id: str
    policy_title: str
    version_id: str
    version_label: str
    section: str
    section_path: tuple[str, ...]
    heading: str
    kind: str
    text: str
    page_start: int
    spans: tuple[tuple[int, int, int], ...]  # (text_start, text_end, page_index)
    reason: str  # "search" or why it was added
    # For an exception clause: the requirement clauses it replaces (stored `excepts` relations).
    excepts: tuple[str, ...] = ()
    reviewed_candidate: bool = False

    def as_prompt(self) -> str:
        excepts = f' excepts="{", ".join(self.excepts)}"' if self.excepts else ""
        return (
            f'<clause id="{self.id}" policy="{self.policy_title}" version="{self.version_label}" '
            f'section="{self.section}" heading="{self.heading}" kind="{self.kind}"{excepts}>\n'
            f"{self.text}\n</clause>"
        )


@dataclass
class Evidence:
    snapshot_id: str
    as_of: date
    clauses: list[EvidenceClause]
    search_hits: int

    def by_id(self) -> dict[str, EvidenceClause]:
        return {c.id: c for c in self.clauses}

    def policies(self) -> list[str]:
        return sorted({c.policy_title for c in self.clauses})


def _evidence(clause: m.Clause, reason: str, excepts: tuple[str, ...] = ()) -> EvidenceClause:
    version = clause.version
    return EvidenceClause(
        id=clause.id,
        policy_title=version.policy.title,
        version_id=version.id,
        version_label=version.label,
        section=clause.clause_key,
        section_path=tuple(clause.section_path),
        heading=clause.heading,
        kind=clause.kind.value,
        text=clause.text,
        page_start=clause.page_start,
        spans=tuple((s.text_start, s.text_end, s.page_index) for s in clause.spans),
        reason=reason,
        excepts=excepts,
        reviewed_candidate=clause.clause_key in reviewed_candidates(version.id, version.provenance),
    )


def retrieve(
    session: Session,
    organization_id: str,
    *,
    snapshot_id: str,
    as_of: date,
    query: str,
    embedder: Embedder | None,
    policy_ids: list[str] | None = None,
) -> Evidence:
    result = search(
        session,
        organization_id,
        SearchRequest(
            question=query[:2000], as_of=as_of, limit=SEARCH_LIMIT, policy_ids=policy_ids
        ),
        embedder,
        snapshot_id=snapshot_id,
    )
    hit_ids = [h.clause.id for h in result.hits]
    chosen: dict[str, str] = {cid: "search" for cid in hit_ids}
    excepts: dict[str, list[str]] = {}

    def add(clause_id: str, reason: str) -> None:
        if clause_id not in chosen and len(chosen) < MAX_CLAUSES:
            chosen[clause_id] = reason

    if hit_ids:
        # Both endpoints must be eligible, including manually reviewed cross-policy links.
        eligible = eligible_version_ids(organization_id, snapshot_id, as_of, policy_ids)
        allowed_ids = set(
            session.scalars(select(m.Clause.id).where(m.Clause.policy_version_id.in_(eligible)))
        )
        relations = session.execute(
            select(
                m.ClauseRelation.source_clause_id,
                m.ClauseRelation.target_clause_id,
                m.ClauseRelation.relation,
                m.ClauseRelation.approved_by,
            ).where(
                or_(
                    m.ClauseRelation.source_clause_id.in_(hit_ids),
                    m.ClauseRelation.target_clause_id.in_(hit_ids),
                )
            )
        ).all()
        for source, target, relation, approved_by in sorted(relations):
            if source not in allowed_ids or target not in allowed_ids:
                continue
            source_clause = session.get_one(m.Clause, source)
            if source_clause.version.provenance.get("managed_upload") and approved_by is None:
                continue
            if relation == m.RelationKind.EXCEPTS:
                excepts.setdefault(source, []).append(target)
            if source in hit_ids:
                add(target, f"cited by {source}")
            elif relation == m.RelationKind.EXCEPTS:
                add(source, f"exception to {target}")
        version_ids = list(dict.fromkeys(h.clause.policy_version_id for h in result.hits))
        definitions = session.scalars(
            select(m.Clause.id)
            .where(
                m.Clause.policy_version_id.in_(version_ids),
                m.Clause.kind == ClauseKind.DEFINITION,
            )
            .order_by(m.Clause.policy_version_id, m.Clause.ordinal)
        ).all()
        for clause_id in definitions:
            add(clause_id, "definition")

    rows = {c.id: c for c in session.scalars(select(m.Clause).where(m.Clause.id.in_(list(chosen))))}
    return Evidence(
        snapshot_id=result.policy_snapshot_id or snapshot_id,
        as_of=as_of,
        clauses=[
            _evidence(rows[cid], reason, tuple(t for t in excepts.get(cid, []) if t in chosen))
            for cid, reason in chosen.items()
        ],
        search_hits=len(hit_ids),
    )
