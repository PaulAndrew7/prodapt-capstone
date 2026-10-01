"""Bounded, dated visualization of stored relationships and saved finding provenance."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from app.api.citations import source_url
from app.api.deps import CurrentPrincipal, DbSession
from app.api.errors import AppError, not_found
from app.domain.policy_management import GraphEdge, GraphNode, PolicyGraph
from app.persistence import models as m
from app.retrieval.search import eligible_version_ids, latest_snapshot_id

router = APIRouter(prefix="/api/v1", tags=["knowledge graph"])
MAX_GRAPH_CLAUSES = 60


@router.get("/policy-graph", response_model=PolicyGraph)
def policy_graph(
    session: DbSession,
    principal: CurrentPrincipal,
    policy_id: Annotated[str | None, Query(max_length=256)] = None,
    as_of: date | None = None,
    snapshot_id: Annotated[str | None, Query(max_length=256)] = None,
    case_id: Annotated[str | None, Query(max_length=256)] = None,
) -> PolicyGraph:
    assessment: dict[str, Any] | None = None
    case = None
    if case_id:
        case = session.get(m.Case, case_id)
        if case is None or case.organization_id != principal.organization_id:
            raise not_found("Case")
        run = session.scalars(
            select(m.AssessmentRun)
            .where(m.AssessmentRun.case_id == case.id, m.AssessmentRun.assessment.is_not(None))
            .order_by(m.AssessmentRun.created_at.desc())
            .limit(1)
        ).first()
        if run is None or not run.assessment:
            raise AppError(
                422, "assessment_required", "Complete an assessment before viewing its graph."
            )
        assessment = run.assessment
        snapshot_id, as_of = run.snapshot_id, date.fromisoformat(assessment["as_of"])
    snapshot_id = snapshot_id or latest_snapshot_id(session, principal.organization_id)
    snapshot = session.get(m.PolicySnapshot, snapshot_id) if snapshot_id else None
    if snapshot is None or snapshot.organization_id != principal.organization_id:
        raise not_found("Policy snapshot")
    as_of = as_of or date.today()
    if policy_id:
        policy = session.get(m.Policy, policy_id)
        if policy is None or policy.organization_id != principal.organization_id:
            raise not_found("Policy")
    versions = list(
        session.scalars(
            select(m.PolicyVersion)
            .where(
                m.PolicyVersion.id.in_(
                    eligible_version_ids(principal.organization_id, snapshot.id, as_of)
                )
            )
            .order_by(m.PolicyVersion.policy_id)
        )
    )
    by_version = {v.id: v for v in versions}
    clauses = list(
        session.scalars(
            select(m.Clause)
            .where(m.Clause.policy_version_id.in_(by_version))
            .order_by(m.Clause.policy_version_id, m.Clause.ordinal)
        )
    )
    by_clause = {c.id: c for c in clauses}
    if policy_id is None and clauses:
        cited = (
            [f.get("requirement_id") for f in assessment.get("findings", [])] if assessment else []
        )
        first = next((by_clause[cid] for cid in cited if cid in by_clause), clauses[0])
        policy_id = by_version[first.policy_version_id].policy_id
    selected = {c.id for c in clauses if by_version[c.policy_version_id].policy_id == policy_id}
    all_relations = list(
        session.scalars(
            select(m.ClauseRelation)
            .where(
                m.ClauseRelation.source_clause_id.in_(by_clause),
                m.ClauseRelation.target_clause_id.in_(by_clause),
                or_(
                    m.ClauseRelation.source_clause_id.in_(selected),
                    m.ClauseRelation.target_clause_id.in_(selected),
                ),
            )
            .order_by(m.ClauseRelation.id)
        )
    )
    wanted = selected | {
        cid for r in all_relations for cid in (r.source_clause_id, r.target_clause_id)
    }
    ordered = [c for c in clauses if c.id in selected] + [
        c for c in clauses if c.id in wanted and c.id not in selected
    ]
    visible = ordered[:MAX_GRAPH_CLAUSES]
    visible_ids = {c.id for c in visible}
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    for c in visible:
        v = by_version[c.policy_version_id]
        p = v.policy
        pid, vid, cid = f"policy:{p.id}", f"version:{v.id}", f"clause:{c.id}"
        href = f"/app/policies/{p.id}/versions/{v.id}"
        if pid not in nodes:
            nodes[pid] = GraphNode(id=pid, kind="policy", label=p.title, href=href)
        if vid not in nodes:
            nodes[vid] = GraphNode(
                id=vid,
                kind="version",
                label=f"{v.label} · {v.effective_from}",
                href=href,
                source_url=source_url(v.id, 0),
                status=v.status.value,
            )
            edges.append(GraphEdge(id=f"has:{vid}", source=pid, target=vid, kind="contains"))
        nodes[cid] = GraphNode(
            id=cid,
            kind="clause",
            label=f"§{c.clause_key} {c.heading}",
            href=f"{href}?clause={c.id}",
            text=c.text,
            source_url=source_url(v.id, c.page_start),
            status=c.kind.value,
        )
        edges.append(GraphEdge(id=f"has:{cid}", source=vid, target=cid, kind="contains"))
    for r in all_relations:
        if r.source_clause_id in visible_ids and r.target_clause_id in visible_ids:
            edges.append(
                GraphEdge(
                    id=r.id,
                    source=f"clause:{r.source_clause_id}",
                    target=f"clause:{r.target_clause_id}",
                    kind=r.relation.value,
                    approved=r.approved_by is not None,
                    provenance=r.provenance,
                )
            )
    if assessment and case:
        case_node = f"case:{case.id}"
        findings = [f for f in assessment["findings"] if f["requirement_id"] in visible_ids]
        if findings:
            nodes[case_node] = GraphNode(
                id=case_node, kind="case", label=case.title, href=f"/app/cases/{case.id}"
            )
        for f in findings:
            fid = f"finding:{assessment['run_id']}:{f['id']}"
            nodes[fid] = GraphNode(
                id=fid,
                kind="finding",
                label=f["title"],
                href=f"/app/cases/{case.id}",
                text=f["rationale"],
                status=f["status"],
            )
            edges.extend(
                [
                    GraphEdge(
                        id=f"source:{fid}",
                        source=f"clause:{f['requirement_id']}",
                        target=fid,
                        kind="supports",
                        provenance="saved assessment",
                    ),
                    GraphEdge(id=f"case:{fid}", source=case_node, target=fid, kind="contains"),
                ]
            )
    return PolicyGraph(
        snapshot_id=snapshot.id,
        as_of=as_of,
        policy_id=policy_id,
        case_id=case_id,
        nodes=list(nodes.values()),
        edges=edges,
        truncated=len(ordered) > len(visible),
        total_clauses=len(ordered),
    )
