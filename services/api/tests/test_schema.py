"""Database invariants that protect traceability (F02)."""

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.persistence import models as m
from app.seed import DEMO_ADMIN_ID, DEMO_ORG_ID, DEMO_SNAPSHOT_ID

pytestmark = pytest.mark.db


def _run_citing(db: Session, clause_id: str) -> m.Citation:
    db.add(
        m.Case(
            id="case_t",
            organization_id=DEMO_ORG_ID,
            owner_id=DEMO_ADMIN_ID,
            title="t",
            business_area="b",
            as_of=date(2026, 9, 25),
        )
    )
    db.flush()
    db.add(
        m.ScenarioRevision(
            id="rev_t",
            case_id="case_t",
            revision_number=1,
            text="scenario",
            created_by=DEMO_ADMIN_ID,
        )
    )
    db.flush()
    db.add(
        m.AssessmentRun(
            id="run_t",
            organization_id=DEMO_ORG_ID,
            case_id="case_t",
            scenario_revision_id="rev_t",
            snapshot_id=DEMO_SNAPSHOT_ID,
            idempotency_key="k1",
            created_by=DEMO_ADMIN_ID,
        )
    )
    db.flush()
    clause = db.get(m.Clause, clause_id)
    assert clause is not None
    citation = m.Citation(
        id="cite_t",
        run_id="run_t",
        policy_version_id=clause.policy_version_id,
        clause_id=clause.id,
        page_index=clause.page_start,
        section_path=clause.section_path,
        quote=clause.text,
        quote_sha256="0" * 64,
        source_url="/x",
    )
    db.add(citation)
    db.flush()
    return citation


def test_historical_citation_keeps_resolving_original_text(db: Session) -> None:
    citation = _run_citing(db, "ds_v1_4_4.2")
    # ds_v2 is published and newer; the citation still resolves the exact v1 clause.
    assert db.get(m.PolicyVersion, "ds_v2") is not None
    clause = db.get(m.Clause, citation.clause_id)
    assert clause is not None and clause.policy_version_id == "ds_v1"
    assert clause.text == citation.quote
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(text("DELETE FROM policy_versions WHERE id = 'ds_v1'"))


def test_unknown_facts_cannot_carry_a_value(db: Session) -> None:
    _run_citing(db, "ds_v1_4_4.2")
    db.add(
        m.Fact(
            id="f1",
            scenario_revision_id="rev_t",
            key="vendor_review",
            label="Vendor review",
            value="approved",
            origin="unknown",
        )
    )
    with pytest.raises(IntegrityError), db.begin_nested():
        db.flush()


def test_idempotency_key_is_unique_per_case(db: Session) -> None:
    _run_citing(db, "ds_v1_4_4.2")
    db.add(
        m.AssessmentRun(
            id="run_t2",
            organization_id=DEMO_ORG_ID,
            case_id="case_t",
            scenario_revision_id="rev_t",
            snapshot_id=DEMO_SNAPSHOT_ID,
            idempotency_key="k1",
            created_by=DEMO_ADMIN_ID,
        )
    )
    with pytest.raises(IntegrityError), db.begin_nested():
        db.flush()


def test_event_sequence_is_unique_and_events_are_immutable(db: Session) -> None:
    _run_citing(db, "ds_v1_4_4.2")
    db.add(m.RunEventRow(id="e1", run_id="run_t", sequence=1, type="run.queued"))
    db.flush()
    with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
        db.execute(text("UPDATE run_events SET type = 'run.completed' WHERE id = 'e1'"))
    db.add(m.RunEventRow(id="e2", run_id="run_t", sequence=1, type="run.started"))
    with pytest.raises(IntegrityError), db.begin_nested():
        db.flush()


def test_audit_log_is_append_only(db: Session) -> None:
    db.add(
        m.AuditEvent(
            id="a1",
            organization_id=DEMO_ORG_ID,
            actor_id=DEMO_ADMIN_ID,
            action="policy.publish",
            target_type="policy_version",
            target_id="ds_v1",
        )
    )
    db.flush()
    for stmt in ("UPDATE audit_events SET action = 'x'", "DELETE FROM audit_events"):
        with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
            db.execute(text(stmt))
