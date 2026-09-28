"""Deterministic workflow rules: verdict aggregation, answers versus inferences, citation
checks and the risk rubric (plan §5.2, §6.3, §7.2). No database or model provider needed,
except the interrupted-run test."""

from collections.abc import Callable
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.contracts import (
    AssessmentStatus,
    FactOrigin,
    Finding,
    RequirementStatus,
    RunState,
    Severity,
    SupportState,
)
from app.persistence import models as m
from app.workflow import risk
from app.workflow.analysis import Answer, EvidenceRef, analyze
from app.workflow.llm import CallBudget, ModelError
from app.workflow.orchestrator import fail_interrupted_runs
from app.workflow.outcome import derive_status
from app.workflow.retrieval import Evidence, EvidenceClause
from app.workflow.validation import check_references
from tests.scripted import DS_42, DS_42_QUOTE, VD_31, ScriptedModel, analysis_reply

S = RequirementStatus
V, U, C, P = (
    SupportState.VALIDATED,
    SupportState.UNSUPPORTED,
    SupportState.CONTRADICTED,
    SupportState.PENDING,
)


def finding(n: int, status: RequirementStatus, support: SupportState, req: str = DS_42) -> Finding:
    return Finding(
        id=f"finding_{n}",
        requirement_id=req,
        title=f"Finding {n}",
        status=status,
        rationale="",
        fact_ids=[],
        citation_ids=[],
        support=support,
        missing_facts=[],
    )


@pytest.mark.parametrize(
    ("findings", "expected"),
    [
        ([(S.VIOLATED, V), (S.UNKNOWN, V)], AssessmentStatus.NON_COMPLIANT),
        ([(S.VIOLATED, V), (S.CONFLICT, V)], AssessmentStatus.NON_COMPLIANT),
        ([(S.CONFLICT, V), (S.UNKNOWN, V)], AssessmentStatus.CONFLICTING_POLICY),
        ([(S.MET, V), (S.UNKNOWN, V)], AssessmentStatus.INSUFFICIENT_INFORMATION),
        ([(S.MET, V), (S.MET, V)], AssessmentStatus.COMPLIANT_WITHIN_SCOPE),
        ([(S.MET, V), (S.NOT_APPLICABLE, V)], AssessmentStatus.COMPLIANT_WITHIN_SCOPE),
        # Unconfirmed decisive claims block compliance; they never decide a breach either.
        ([(S.MET, V), (S.MET, U)], AssessmentStatus.INSUFFICIENT_INFORMATION),
        ([(S.MET, V), (S.VIOLATED, C)], AssessmentStatus.INSUFFICIENT_INFORMATION),
        ([(S.VIOLATED, P)], AssessmentStatus.INSUFFICIENT_INFORMATION),
        # An unknown that validation found irrelevant does not block a result.
        ([(S.MET, V), (S.UNKNOWN, U)], AssessmentStatus.COMPLIANT_WITHIN_SCOPE),
        ([(S.NOT_APPLICABLE, V)], AssessmentStatus.OUT_OF_SCOPE),
        ([], AssessmentStatus.OUT_OF_SCOPE),
    ],
)
def test_verdict_rules(
    findings: list[tuple[RequirementStatus, SupportState]], expected: AssessmentStatus
) -> None:
    items = [finding(n, status, support) for n, (status, support) in enumerate(findings)]
    assert derive_status(items) == expected


def clause(cid: str, text: str, title: str = "Customer Data Sharing Policy") -> EvidenceClause:
    return EvidenceClause(
        id=cid,
        policy_title=title,
        version_id=cid.split("_")[0] + "_v1",
        version_label="v1",
        section=cid.rsplit("_", 1)[1],
        section_path=(cid.rsplit("_", 1)[1],),
        heading="Heading",
        kind="requirement",
        text=text,
        page_start=0,
        spans=((0, 30, 0), (30, 400, 1)),  # the clause crosses a page break
        reason="search",
    )


DS_TEXT = (
    "External sharing of customer data requires written approval from the data owner, "
    "recorded in the data-sharing register before any transfer takes place."
)
EVIDENCE = Evidence(
    snapshot_id="snap",
    as_of=date(2026, 9, 26),
    clauses=[
        clause(DS_42, DS_TEXT),
        clause(VD_31, "A vendor must hold Approved status before receiving customer data."),
    ],
    search_hits=2,
)


def test_citations_are_built_from_stored_text_and_bad_references_are_caught() -> None:
    findings = [
        finding(1, S.VIOLATED, P),
        finding(2, S.UNKNOWN, P, req=VD_31),
        finding(3, S.VIOLATED, P, req="zz_v1_9_9.9"),
    ]
    proposed = {
        "finding_1": [
            EvidenceRef(clause_id=DS_42, quote=DS_42_QUOTE),
            EvidenceRef(clause_id="zz_v1_9_9.9", quote="made up"),
        ],
        # A paraphrase is not a quote: the whole stored clause is cited instead.
        "finding_2": [EvidenceRef(clause_id=VD_31, quote="vendors need approval first")],
        "finding_3": [EvidenceRef(clause_id="zz_v1_9_9.9", quote="made up")],
    }
    v = check_references(findings, proposed, EVIDENCE)
    by_id = {c.id: c for c in v.citations}
    f1, f2, f3 = v.findings
    assert [by_id[c].quote for c in f1.citation_ids] == [DS_42_QUOTE]
    # The quote starts in the second span, so the citation opens page 2.
    assert by_id[f1.citation_ids[0]].page_index == 1
    assert by_id[f1.citation_ids[0]].source_url.endswith("source?page=2")
    assert by_id[f2.citation_ids[0]].quote == EVIDENCE.clauses[1].text
    assert f3.support == U and f3.citation_ids == []
    assert (v.invalid_references, v.quote_mismatches) == (2, 1)
    # Unsupported claims still block compliance downstream.
    assert derive_status([f1.model_copy(update={"status": S.MET, "support": V}), f3]) == (
        AssessmentStatus.INSUFFICIENT_INFORMATION
    )


def test_requirement_clause_is_cited_even_if_the_model_forgot() -> None:
    v = check_references([finding(1, S.VIOLATED, P)], {"finding_1": []}, EVIDENCE)
    assert [c.clause_id for c in v.citations] == [DS_42]
    assert v.findings[0].support == P


def test_answers_override_the_model_and_inferences_stay_unconfirmed() -> None:
    reply = analysis_reply(questions=False)
    # The model claims a vendor status nobody stated and infers a purpose.
    reply["facts"] = [
        *reply["facts"][:2],
        {
            "key": "vendor_review_status",
            "label": "Vendor review",
            "value": "Approved",
            "origin": "provided",
        },
        {"key": "purpose", "label": "Purpose", "value": "Analytics", "origin": "inferred"},
    ]
    budget = CallBudget(ScriptedModel(analysis=[reply]), max_calls=4, deadline_seconds=60)
    result = analyze(
        budget,
        scenario="...",
        as_of="2026-09-26",
        answers=[Answer("q_1", "vendor_review_status", "Is the vendor approved?", None, "msg_1")],
        evidence=EVIDENCE,
        allow_questions=False,
    )
    facts = {f.key: f for f in result.facts}
    vendor = facts["vendor_review_status"]
    assert (vendor.value, vendor.origin, vendor.confirmed) == (None, FactOrigin.UNKNOWN, True)
    assert vendor.source_message_id == "msg_1"
    assert facts["purpose"].origin == FactOrigin.INFERRED and not facts["purpose"].confirmed
    assert facts["data_owner_approval"].confirmed
    assert result.questions == []  # no second clarification round


def test_questions_are_capped_at_three() -> None:
    reply = analysis_reply()
    reply["questions"] = reply["questions"] * 5
    budget = CallBudget(ScriptedModel(analysis=[reply]), max_calls=4, deadline_seconds=60)
    result = analyze(
        budget,
        scenario="...",
        as_of="2026-09-26",
        answers=[],
        evidence=EVIDENCE,
        allow_questions=True,
    )
    assert [q.id for q in result.questions] == ["q_1", "q_2", "q_3"]


def test_call_budget_is_enforced() -> None:
    model = ScriptedModel(analysis=["{}", "{}"])
    budget = CallBudget(model, max_calls=1, deadline_seconds=60)
    with pytest.raises(ModelError) as exc:
        analyze(
            budget,
            scenario="...",
            as_of="2026-09-26",
            answers=[],
            evidence=EVIDENCE,
            allow_questions=False,
        )
    assert exc.value.code == "budget_exhausted" and len(model.calls) == 1


def test_risk_rubric() -> None:
    clauses = {
        DS_42: clause(DS_42, DS_TEXT),
        "ex_v1_2_2.1": clause(
            "ex_v1_2_2.1", "Claims above 750 must be approved by a director.", "Expenses Policy"
        ),
        "gv_v1_3_3.1": clause(
            "gv_v1_3_3.1", "Staff should log hospitality they receive.", "Gifts Policy"
        ),
    }
    findings = [
        finding(1, S.VIOLATED, V, "gv_v1_3_3.1"),
        finding(2, S.VIOLATED, V, "ex_v1_2_2.1"),
        finding(3, S.VIOLATED, V, DS_42),
        finding(4, S.UNKNOWN, V, DS_42),
        finding(5, S.VIOLATED, U, DS_42),
        finding(6, S.CONFLICT, P, "ex_v1_2_2.1"),
    ]
    risks = risk.assess(findings, clauses)
    assert [(r.finding_ids[0], r.severity) for r in risks] == [
        ("finding_3", Severity.HIGH),
        ("finding_2", Severity.MEDIUM),
        ("finding_6", Severity.MEDIUM),
        ("finding_1", Severity.LOW),
    ]
    assert {r.likelihood.value for r in risks} == {"unknown"}
    assert [r.id for r in risks] == ["risk_1", "risk_2", "risk_3", "risk_4"]


@pytest.mark.db
def test_interrupted_runs_fail_on_startup(
    db: Session, session_factory: Callable[[], Session]
) -> None:
    case = m.Case(
        id="case_t",
        organization_id="org_kestrel",
        owner_id="user_demo_admin",
        title="t",
        business_area="x",
        as_of=date(2026, 9, 26),
    )
    db.add(case)
    db.flush()
    rev = m.ScenarioRevision(
        id="rev_t", case_id="case_t", revision_number=1, text="t", created_by="user_demo_admin"
    )
    db.add(rev)
    db.flush()
    for state in (RunState.RUNNING, RunState.WAITING_FOR_USER):
        db.add(
            m.AssessmentRun(
                id=f"run_{state.value}",
                organization_id="org_kestrel",
                case_id="case_t",
                scenario_revision_id="rev_t",
                snapshot_id="snapshot_demo_v1",
                state=state,
                idempotency_key=state.value,
                created_by="user_demo_admin",
            )
        )
    db.commit()
    assert fail_interrupted_runs(session_factory) == 1
    db.expire_all()
    runs = {
        r.id: r
        for r in db.scalars(select(m.AssessmentRun).where(m.AssessmentRun.case_id == "case_t"))
    }
    assert runs["run_running"].state == RunState.FAILED
    assert runs["run_running"].error["code"] == "interrupted"  # type: ignore[index]
    # A run waiting for the user keeps its questions and can still be answered.
    assert runs["run_waiting_for_user"].state == RunState.WAITING_FOR_USER
