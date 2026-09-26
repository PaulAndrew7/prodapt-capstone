"""Evidence search over one policy snapshot (plan §6.2; first pass of F05).

Lexical (Postgres full-text) and dense (pgvector cosine, exact scan) channels run with the
same snapshot, organization, date and scope filters, then merge by reciprocal rank fusion:
score(d) = sum(1 / (k + rank_i(d))), k = 60. RRF is a tunable rank-combination heuristic;
its score is not a probability. Results are deduplicated to the best chunk per clause.
"""

import time
from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import Select, and_, func, literal_column, or_, select
from sqlalchemy.orm import Session

from app.api.citations import citation_for, clause_contract
from app.domain.contracts import PolicyVersionStatus, SearchHit, SearchRequest, SearchResponse
from app.persistence import models as m
from app.retrieval.embeddings import Embedder

RRF_K = 60
CHANNEL_DEPTH = 20


@dataclass
class _Candidate:
    chunk_id: str
    clause_id: str
    lexical_rank: int | None = None
    dense_rank: int | None = None

    @property
    def score(self) -> float:
        return sum(1.0 / (RRF_K + r) for r in (self.lexical_rank, self.dense_rank) if r)


def latest_snapshot_id(session: Session, organization_id: str) -> str | None:
    return session.scalar(
        select(m.PolicySnapshot.id)
        .where(m.PolicySnapshot.organization_id == organization_id)
        .order_by(m.PolicySnapshot.created_at.desc())
        .limit(1)
    )


def _eligible_chunks(
    organization_id: str, snapshot_id: str, as_of: date, policy_ids: list[str] | None
) -> Select[str, str]:
    q = (
        select(m.Chunk.id, m.Chunk.clause_id)
        .join(m.PolicyVersion, m.PolicyVersion.id == m.Chunk.policy_version_id)
        .join(m.Policy, m.Policy.id == m.PolicyVersion.policy_id)
        .join(
            m.SnapshotVersion,
            and_(
                m.SnapshotVersion.policy_version_id == m.PolicyVersion.id,
                m.SnapshotVersion.snapshot_id == snapshot_id,
            ),
        )
        .where(
            m.Policy.organization_id == organization_id,
            m.PolicyVersion.status != PolicyVersionStatus.DRAFT,
            m.PolicyVersion.effective_from <= as_of,
            or_(m.PolicyVersion.effective_to.is_(None), m.PolicyVersion.effective_to >= as_of),
        )
    )
    if policy_ids:
        q = q.where(m.Policy.id.in_(policy_ids))
    return q


def search(
    session: Session, organization_id: str, req: SearchRequest, embedder: Embedder | None
) -> SearchResponse:
    started = time.perf_counter()
    snapshot_id = latest_snapshot_id(session, organization_id)
    if snapshot_id is None:
        return SearchResponse(
            question=req.question, policy_snapshot_id=None, hits=[], channels=[], latency_ms=0
        )
    as_of = req.as_of or date.today()
    base = _eligible_chunks(organization_id, snapshot_id, as_of, req.policy_ids)
    candidates: dict[str, _Candidate] = {}

    # Lexical: OR together the query's stemmed lexemes so natural questions still match.
    tsquery = func.to_tsquery(
        "english",
        select(func.string_agg(func.quote_literal(literal_column("lexeme")), " | "))
        .select_from(
            func.unnest(func.tsvector_to_array(func.to_tsvector("english", req.question))).alias(
                "lexeme"
            )
        )
        .scalar_subquery(),
    )
    rank = func.ts_rank_cd(m.Chunk.search_vector, tsquery)
    lexical = session.execute(
        base.where(m.Chunk.search_vector.op("@@")(tsquery))
        .order_by(rank.desc(), m.Chunk.id)
        .limit(CHANNEL_DEPTH)
    ).all()
    for i, (chunk_id, clause_id) in enumerate(lexical, start=1):
        candidates[chunk_id] = _Candidate(chunk_id, clause_id, lexical_rank=i)

    channels: list[Literal["lexical", "dense"]] = ["lexical"]
    if embedder is not None:
        vector = embedder.embed_query(req.question)
        dense = session.execute(
            base.where(m.Chunk.embedding.is_not(None))
            .order_by(m.Chunk.embedding.cosine_distance(vector), m.Chunk.id)
            .limit(CHANNEL_DEPTH)
        ).all()
        channels.append("dense")
        for i, (chunk_id, clause_id) in enumerate(dense, start=1):
            candidates.setdefault(chunk_id, _Candidate(chunk_id, clause_id)).dense_rank = i

    best: dict[str, _Candidate] = {}
    for c in candidates.values():
        if c.clause_id not in best or c.score > best[c.clause_id].score:
            best[c.clause_id] = c
    ranked = sorted(best.values(), key=lambda c: (-c.score, c.clause_id))[: req.limit]

    clauses = {
        c.id: c
        for c in session.scalars(
            select(m.Clause).where(m.Clause.id.in_([r.clause_id for r in ranked]))
        )
    }
    hits = []
    for n, cand in enumerate(ranked, start=1):
        clause = clauses[cand.clause_id]
        version = clause.version
        hits.append(
            SearchHit(
                clause=clause_contract(clause),
                policy_title=version.policy.title,
                version_label=version.label,
                chunk_id=cand.chunk_id,
                score=round(cand.score, 6),
                lexical_rank=cand.lexical_rank,
                dense_rank=cand.dense_rank,
                citation=citation_for(f"hit_{n}", clause, clause.text),
            )
        )
    return SearchResponse(
        question=req.question,
        policy_snapshot_id=snapshot_id,
        hits=hits,
        channels=channels,
        latency_ms=round((time.perf_counter() - started) * 1000),
    )
