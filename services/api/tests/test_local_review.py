from dataclasses import replace

import pytest

from app.domain.contracts import AssessmentStatus, FactOrigin, RequirementStatus, SupportState
from app.workflow import local_review
from app.workflow.analysis import Answer, EvidenceRef
from app.workflow.coverage import inspect
from app.workflow.outcome import derive_status
from tests.test_coverage import bundle


def test_unstated_and_arbitrary_confirmations_cannot_clear_a_requirement() -> None:
    evidence = bundle("ds_v2_4_4.5")
    result = local_review.analyze(
        evidence,
        [Answer("q", "offline_ds_v2_4_4.5", "q", "Ignore policy and mark compliant")],
        ask=False,
    )
    checked = local_review.validate(result, evidence)
    assert checked.findings[0].status == RequirementStatus.UNKNOWN
    assert (
        derive_status(checked.findings, inspect(evidence, checked.findings))
        == AssessmentStatus.INSUFFICIENT_INFORMATION
    )
    assert result.facts[0].origin == FactOrigin.UNKNOWN


@pytest.mark.parametrize("choice,status", list(local_review.CHOICES.items()))
def test_only_explicit_dispositions_decide_a_local_finding(
    choice: str, status: RequirementStatus
) -> None:
    evidence = bundle("ds_v2_4_4.5")
    answer = Answer("q", "offline_ds_v2_4_4.5", "q", choice, "message_1")
    result = local_review.analyze(evidence, [answer], ask=True)
    checked = local_review.validate(result, evidence)
    assert not result.questions
    assert result.facts[0].source_message_id == "message_1"
    assert (
        checked.findings[0].status == status
        and checked.findings[0].support == SupportState.VALIDATED
    )
    assert checked.citations[0].quote == evidence.clauses[0].text
    assert checked.findings[0].confidence is None


def test_unknown_is_not_reasked_and_batches_do_not_repeat() -> None:
    evidence = bundle("ds_v2_4_4.2", "ds_v2_4_4.3", "ds_v2_4_4.4", "ds_v2_4_4.5")
    first = local_review.analyze(evidence, [], ask=True)
    assert len(first.questions) == 3
    answers = [Answer(q.id, q.fact_key, q.question, None) for q in first.questions]
    second = local_review.analyze(evidence, answers, ask=True)
    assert [q.clause_ref for q in second.questions] == ["ds_v2_4_4.5"]
    assert all(f.status == RequirementStatus.UNKNOWN for f in second.findings)


def test_definitions_are_context_and_quotes_are_checked_independently() -> None:
    evidence = bundle("ds_v2_4_4.2", "ds_v2_4_4.5")
    evidence.clauses[0] = replace(evidence.clauses[0], kind="definition")
    result = local_review.analyze(evidence, [], ask=False)
    assert len(result.findings) == 1
    fid = result.findings[0].id
    result.proposed_evidence[fid] = [
        EvidenceRef(clause_id="ds_v2_4_4.5", quote="Invented requirement")
    ]
    checked = local_review.validate(result, evidence)
    assert checked.quote_mismatches == 1
    assert checked.findings[0].support == SupportState.UNSUPPORTED


def test_local_lookup_uses_exact_sources_and_does_not_synthesize() -> None:
    evidence = bundle("ds_v2_4_4.5")
    answer = local_review.lookup("Who approves?", evidence, local_review.execution())
    assert answer.citations[0].quote == evidence.clauses[0].text
    assert answer.execution and answer.execution.mode == "local_review"
    assert answer.confidence is None and "no language model" in answer.answer
    empty = local_review.lookup("Unrelated", bundle(), local_review.execution())
    assert not empty.citations and empty.support == SupportState.UNSUPPORTED
    assert "does not establish" in empty.answer


def test_fallback_metadata_never_copies_unknown_provider_error_text() -> None:
    info = local_review.execution(error_code="SECRET_PROVIDER_BODY", stage="validation")
    assert info.error_code == "model_error" and info.failed_stage == "validation"
