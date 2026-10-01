"""Coverage checks omissions independently of generated findings and citations."""

import re
from dataclasses import replace
from datetime import date

import pytest

from app.config import REPO_ROOT
from app.domain.contracts import AssessmentStatus, ClauseKind, RequirementStatus, SupportState
from app.workflow.analysis import analyze, build_prompt
from app.workflow.confidence import score_assessment
from app.workflow.coverage import REVIEWED_GENERAL_CLAUSES, inspect
from app.workflow.llm import CallBudget
from app.workflow.outcome import derive_status, summarize
from app.workflow.retrieval import Evidence
from tests.scripted import ScriptedModel
from tests.test_workflow_rules import clause, finding

S = RequirementStatus
V = SupportState


def bundle(*ids: str) -> Evidence:
    return Evidence(
        "snapshot",
        date(2026, 10, 1),
        [
            replace(
                clause(cid, "The recipient must record a retention period."),
                version_id="ds_v2",
                version_label="v2",
                kind=ClauseKind.REQUIREMENT,
            )
            for cid in ids
        ],
        len(ids),
    )


def test_omitted_requirement_blocks_clearance_without_inventing_a_fact() -> None:
    evidence = bundle("ds_v2_4_4.2", "ds_v2_4_4.5")
    findings = [finding(1, S.MET, V.VALIDATED, "ds_v2_4_4.2")]
    report = inspect(evidence, findings)
    assert report.unresolved_clause_ids == ["ds_v2_4_4.5"]
    assert (report.candidate_count, report.accounted_count) == (2, 1)
    assert report.rows[1].state == "unassessed"
    assert report.rows[1].finding_ids == []
    assert report.rows[1].source_url.startswith("/api/v1/policy-versions/ds_v2/source?")
    assert report.rows[1].text == evidence.clauses[1].text
    status = derive_status(findings, report)
    assert status == AssessmentStatus.INSUFFICIENT_INFORMATION
    summary = summarize(status, findings, report)
    assert "coverage gap" in summary and "missing facts" not in summary
    score = score_assessment(status, findings, evidence, report)
    assert score.score == 0 and "incomplete" in score.basis
    assert findings[0].status == S.MET and findings[0].missing_facts == []


def test_a_citation_is_not_a_requirement_disposition() -> None:
    findings = [finding(1, S.MET, V.VALIDATED, "ds_v2_4_4.2")]
    findings[0].citation_ids = ["cite_for_4.2", "cite_for_4.5"]
    report = inspect(bundle("ds_v2_4_4.2", "ds_v2_4_4.5"), findings)
    assert report.rows[1].state == "unassessed"


@pytest.mark.parametrize("support", [V.PENDING, V.CONTRADICTED, V.UNSUPPORTED])
def test_unconfirmed_exclusion_cannot_clear_a_candidate(support: SupportState) -> None:
    findings = [finding(1, S.NOT_APPLICABLE, support, "ds_v2_4_4.5")]
    report = inspect(bundle("ds_v2_4_4.5"), findings)
    assert report.accounted_count == 0 and report.rows[0].state == "unconfirmed"
    assert derive_status(findings, report) == AssessmentStatus.INSUFFICIENT_INFORMATION


def test_validated_exception_exclusion_is_accounted_for() -> None:
    evidence = bundle("ds_v2_4_4.2", "ds_v2_4_4.4")
    evidence.clauses[1] = replace(evidence.clauses[1], kind=ClauseKind.EXCEPTION)
    findings = [
        finding(1, S.NOT_APPLICABLE, V.VALIDATED, "ds_v2_4_4.2"),
        finding(2, S.MET, V.VALIDATED, "ds_v2_4_4.4"),
    ]
    report = inspect(evidence, findings)
    assert report.rows[0].state == "not_applicable"
    assert report.accounted_count == 2 and not report.unresolved_clause_ids
    assert derive_status(findings, report) == AssessmentStatus.COMPLIANT_WITHIN_SCOPE


@pytest.mark.parametrize(
    ("requirement_status", "expected"),
    [
        (S.VIOLATED, AssessmentStatus.NON_COMPLIANT),
        (S.CONFLICT, AssessmentStatus.CONFLICTING_POLICY),
    ],
)
def test_established_breach_or_conflict_survives_other_omissions(
    requirement_status: RequirementStatus, expected: AssessmentStatus
) -> None:
    findings = [finding(1, requirement_status, V.VALIDATED, "ds_v2_4_4.2")]
    report = inspect(bundle("ds_v2_4_4.2", "ds_v2_4_4.5"), findings)
    assert report.unresolved_clause_ids and derive_status(findings, report) == expected


def test_no_emitted_findings_does_not_prove_out_of_scope() -> None:
    report = inspect(bundle("ds_v2_4_4.5"), [])
    assert derive_status([], report) == AssessmentStatus.INSUFFICIENT_INFORMATION


def test_context_is_not_an_obligation_but_reviewed_retention_clause_is() -> None:
    evidence = bundle("rd_v1_5_5.1", "ds_v2_4_4.1", "ds_v2_2_2.1")
    evidence.clauses = [
        replace(
            evidence.clauses[0],
            kind=ClauseKind.GENERAL,
            reviewed_candidate=True,
            text="Customer claim records are retained for seven years, then deleted.",
        ),
        replace(evidence.clauses[1], kind=ClauseKind.DEFINITION),
        replace(evidence.clauses[2], kind=ClauseKind.GENERAL),
    ]
    report = inspect(evidence, [finding(1, S.MET, V.VALIDATED, "ds_v2_4_4.1")])
    assert [r.clause_id for r in report.rows] == ["rd_v1_5_5.1"]
    assert report.rows[0].candidate_basis == "reviewed_corpus"


def test_disagreeing_findings_do_not_account_for_a_candidate() -> None:
    findings = [finding(1, S.MET, V.VALIDATED), finding(2, S.NOT_APPLICABLE, V.VALIDATED)]
    report = inspect(bundle(findings[0].requirement_id), findings)
    assert report.rows[0].state == "unconfirmed" and "disagree" in report.rows[0].note


def test_unknown_is_assessed_but_still_not_compliant() -> None:
    findings = [finding(1, S.UNKNOWN, V.VALIDATED, "ds_v2_4_4.5")]
    report = inspect(bundle("ds_v2_4_4.5"), findings)
    assert report.accounted_count == 1 and not report.unresolved_clause_ids
    assert derive_status(findings, report) == AssessmentStatus.INSUFFICIENT_INFORMATION


def test_empty_evidence_and_legacy_status_rules_remain_readable() -> None:
    report = inspect(bundle(), [])
    assert report.candidate_count == report.accounted_count == 0
    assert derive_status([], report) == AssessmentStatus.OUT_OF_SCOPE
    assert (
        derive_status([finding(1, S.MET, V.VALIDATED)]) == AssessmentStatus.COMPLIANT_WITHIN_SCOPE
    )


def test_reviewed_catalog_only_names_real_policy_clauses() -> None:
    clause_ids = {
        f"{path.stem}_{section}_{section}.{sub}"
        for path in (REPO_ROOT / "data/demo/policies").glob("*.md")
        for section, sub in re.findall(
            r"^## (\d+)\.(\d+) ", path.read_text(encoding="utf-8"), re.MULTILINE
        )
    }
    assert clause_ids >= REVIEWED_GENERAL_CLAUSES


def test_analysis_checklist_names_candidates_without_turning_context_into_rules() -> None:
    evidence = bundle("ds_v2_4_4.5", "rd_v1_5_5.1", "ds_v2_4_4.1")
    evidence.clauses[1] = replace(
        evidence.clauses[1], kind=ClauseKind.GENERAL, reviewed_candidate=True
    )
    evidence.clauses[2] = replace(evidence.clauses[2], kind=ClauseKind.DEFINITION)
    prompt = build_prompt("An external share", "2026-10-01", [], evidence, False)
    checklist = prompt.split("Coverage checklist", 1)[1].split("Retrieved clauses", 1)[0]
    assert "ds_v2_4_4.5" in checklist and "rd_v1_5_5.1" in checklist
    assert "ds_v2_4_4.1" not in checklist


def test_out_of_scope_exclusions_reach_validation_instead_of_being_discarded() -> None:
    reply = {
        "in_scope": False,
        "facts": [],
        "questions": [],
        "findings": [
            {
                "requirement_clause_id": "ds_v2_4_4.5",
                "title": "No external share",
                "evidence": [
                    {"clause_id": "ds_v2_4_4.5", "quote": "must record a retention period"}
                ],
                "fact_keys": [],
                "rationale": "The described activity involves no external share.",
                "status": "not_applicable",
                "missing_facts": [],
            }
        ],
    }
    model = ScriptedModel(analysis=[reply])
    result = analyze(
        CallBudget(model, max_calls=2, deadline_seconds=60),
        scenario="Walking a dog",
        as_of="2026-10-01",
        answers=[],
        evidence=bundle("ds_v2_4_4.5"),
        allow_questions=False,
    )
    assert not result.in_scope
    assert len(result.findings) == 1 and result.findings[0].status == S.NOT_APPLICABLE
    assert result.findings[0].support == V.PENDING  # Still needs semantic validation.
