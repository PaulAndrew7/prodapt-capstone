"""Reporting/preflight regressions with synthetic test inputs, never the held-out answers."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from app import cli
from app import evaluation as ev
from tests.scripted import ScriptedModel


@pytest.fixture
def inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "evaluation"
    for split in ("dev", "test"):
        folder = root / split
        folder.mkdir(parents=True)
        (folder / "scenarios.json").write_text(
            json.dumps(
                [
                    {"id": f"{split}-1", "review": "reviewed"},
                    {"id": f"{split}-2", "review": "disputed"},
                    {"id": f"{split}-3", "review": "reviewed"},
                ]
            ),
            encoding="utf-8",
        )
    monkeypatch.setattr(ev, "EVAL_DIR", root)
    monkeypatch.setattr(ev, "DOCS_DIR", tmp_path / "reports")
    return root


def result(identifier: str = "dev-1", **values: Any) -> ev.ScenarioResult:
    defaults = dict(
        id=identifier,
        category="test",
        acceptable_status=["non_compliant"],
        expected_clauses=["clause"],
        top10_hybrid=["clause"],
        recall_hybrid=1.0,
        recall_lexical=1.0,
        recall_bundle=1.0,
        requirements_labelled=2,
    )
    return ev.ScenarioResult(**(defaults | values))


@pytest.mark.parametrize("limit", [0, -1])
def test_invalid_limit_precedes_database_setup(
    inputs: Path, monkeypatch: pytest.MonkeyPatch, limit: int
) -> None:
    def forbidden(*_: Any) -> None:
        pytest.fail("Database setup must not run")

    monkeypatch.setattr(cli, "cmd_migrate", forbidden)
    monkeypatch.setattr(cli, "get_settings", forbidden)
    assert cli.cmd_evaluate(argparse.Namespace(split="dev", limit=limit)) == 1


def test_disputed_scenarios_are_excluded_before_limit(inputs: Path) -> None:
    assert [s["id"] for s in ev.select_scenarios("dev", 2)] == ["dev-1", "dev-3"]


def test_heldout_requires_review_of_all_eligible_labels(inputs: Path) -> None:
    path = inputs / "test" / "scenarios.json"
    path.write_text(
        json.dumps(
            [{"id": "test-1", "review": "reviewed"}, {"id": "test-2", "review": "authored"}]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="owner review"):
        ev.select_scenarios("test", 1)


def test_reviewed_heldout_can_be_selected_without_running_it(inputs: Path) -> None:
    assert len(ev.select_scenarios("test")) == 2


def test_summary_counts_only_reviewed_records_actually_evaluated(inputs: Path) -> None:
    summary = ev.summarize("dev", "snapshot", [result()], None, None)
    assert summary["scenarios"] == summary["reviewed_labels"] == 1
    assert summary["excluded_disputed"] == 1


def test_report_provenance_hashes_the_input_files(inputs: Path) -> None:
    summary = ev.summarize("dev", "snapshot", [result()], None, None)
    assert (
        summary["scenario_sha256"]
        == hashlib.sha256((inputs / "dev/scenarios.json").read_bytes()).hexdigest()
    )
    assert (
        summary["corpus_manifest_sha256"]
        == hashlib.sha256((ev.REPO_ROOT / "data/demo/manifest.json").read_bytes()).hexdigest()
    )


def test_repeated_reports_preserve_raw_results(inputs: Path) -> None:
    rows = [result()]
    summary = ev.summarize("dev", "snapshot", rows, None, None)
    _, first = ev.write_report(summary, rows)
    original = first.read_bytes()
    rows[0].recall_hybrid = 0.0
    report, second = ev.write_report(summary, rows)
    assert first != second and first.read_bytes() == original
    assert second.name in report.read_text(encoding="utf-8")


def test_no_embeddings_report_does_not_claim_hybrid_retrieval(inputs: Path) -> None:
    rows = [result()]
    report, _ = ev.write_report(ev.summarize("dev", "snapshot", rows, None, None), rows)
    text = report.read_text(encoding="utf-8")
    assert "Recall@10, keyword only (embeddings disabled)" in text
    assert "Recall@10, hybrid" not in text


def test_failed_runs_remain_in_accuracy_and_requirement_denominators(inputs: Path) -> None:
    rows = [
        result(run_state="completed", status_ok=True, requirements_matched=2),
        result("dev-3", run_state="failed", status_ok=False, requirements_labelled=3),
    ]
    summary = ev.summarize("dev", "snapshot", rows, ScriptedModel(), None)
    assert summary["status_correct"] == 1 and summary["scenarios"] == 2
    assert summary["requirements_matched"] == 2 and summary["requirements_labelled"] == 5
    assert summary["completed"] == 1 and summary["failed"] == 1


def test_only_a_scope_refusal_counts_as_an_out_of_scope_result() -> None:
    assert ev.declined_status({"code": "request_out_of_scope", "message": "x"}) == "out_of_scope"
    assert ev.declined_status({"code": "request_redirected", "message": "x"}) is None
    assert ev.declined_status({"code": "model_timeout", "message": "x"}) is None
    assert ev.declined_status(None) is None


def test_report_marks_runs_declined_by_the_input_check(inputs: Path) -> None:
    rows = [
        result(
            run_state="failed",
            acceptable_status=["out_of_scope"],
            status="out_of_scope",
            status_ok=True,
            error="request_out_of_scope: I couldn't connect this request",
        ),
        result("dev-3", run_state="failed", status_ok=False, error="request_redirected: no"),
    ]
    summary = ev.summarize("dev", "snapshot", rows, ScriptedModel(), None)
    assert summary["status_correct"] == 1 and summary["failed"] == 2
    text = ev.write_report(summary, rows)[0].read_text(encoding="utf-8")
    assert "out_of_scope (declined by the input check) ✓" in text
    assert "request_redirected: no ✗" in text


def test_report_escapes_error_text_in_tables(inputs: Path) -> None:
    rows = [result(run_state="failed", error="bad | reply\n<script>oops</script>")]
    report, _ = ev.write_report(ev.summarize("dev", "snapshot", rows, ScriptedModel(), None), rows)
    text = report.read_text(encoding="utf-8")
    assert "bad &#124; reply &lt;script&gt;" in text
    assert "<script>" not in text


def test_manual_review_excludes_nondecisive_findings() -> None:
    findings = [
        {
            "requirement_id": f"r-{support}-{status}",
            "status": status,
            "support": support,
            "rationale": "claim",
            "citation_ids": ["c"],
        }
        for support in ("validated", "unsupported", "contradicted", "pending")
        for status in ("met", "violated", "unknown", "conflict", "not_applicable")
    ]
    claims = ev._decisive_claims(
        {"findings": findings, "citations": [{"id": "c", "clause_id": "clause", "quote": "text"}]}
    )
    assert {c["status"] for c in claims} == {"met", "violated", "conflict"}
    assert len(claims) == 3 and all(c["support"] == "validated" for c in claims)
    assert all(c["supported_by_reviewer"] is None for c in claims)


def test_accuracy_is_reported_per_confidence_band(inputs: Path) -> None:
    rows = [
        result(
            run_state="completed",
            status_ok=True,
            confidence_score=90,
            confidence_band="high",
            finding_bands=[
                {"requirement_id": "a", "band": "high", "score": 90, "matched": True},
                {"requirement_id": "b", "band": "low", "score": 30, "matched": False},
            ],
        ),
        result("dev-3", run_state="completed", status_ok=False, confidence_band="high"),
        result("dev-4", run_state="failed", status_ok=False),  # no score: not in any band
    ]
    summary = ev.summarize("dev", "snapshot", rows, ScriptedModel(), None)
    assert summary["by_band"]["high"] == {
        "results": 2,
        "results_correct": 1,
        "findings": 1,
        "findings_matched": 1,
    }
    assert summary["by_band"]["low"]["findings"] == 1
    assert summary["by_band"]["low"]["findings_matched"] == 0
    report, _ = ev.write_report(summary, rows)
    text = report.read_text(encoding="utf-8")
    assert "| High | 1/2 (50%) | 1/1 (100%) |" in text
    assert "| Medium | n/a | n/a |" in text
    assert "| 90 high |" in text


def test_unjustified_clearance_includes_unknown_and_conflict_labels(inputs: Path) -> None:
    rows = [
        result(
            "dev-1",
            run_state="completed",
            status="compliant_within_scope",
            acceptable_status=["insufficient_information"],
            false_compliant=False,
        ),
        result(
            "dev-3",
            run_state="completed",
            status="compliant_within_scope",
            acceptable_status=["conflicting_policy"],
            false_compliant=False,
        ),
        result("dev-4", run_state="failed", acceptable_status=["non_compliant"]),
        result(
            "dev-5",
            run_state="completed",
            status="compliant_within_scope",
            acceptable_status=["compliant_within_scope", "insufficient_information"],
        ),
    ]
    summary = ev.summarize("dev", "snapshot", rows, ScriptedModel(), None)
    assert summary["false_compliant"] == 0
    assert summary["unjustified_compliant"] == 2 and summary["labelled_no_clearance"] == 3
    report, _ = ev.write_report(summary, rows)
    assert "Unjustified compliant results | 2 of 3" in report.read_text(encoding="utf-8")


def test_coverage_reporting_distinguishes_abstention_from_correctness(inputs: Path) -> None:
    rows = [
        result(
            run_state="completed",
            status="insufficient_information",
            acceptable_status=["compliant_within_scope"],
            coverage_candidates=3,
            coverage_accounted=1,
            coverage_unresolved=2,
        ),
        result(
            "dev-3",
            run_state="completed",
            status="insufficient_information",
            acceptable_status=["compliant_within_scope", "insufficient_information"],
            coverage_candidates=1,
            coverage_accounted=1,
            coverage_unresolved=0,
        ),
        result("dev-4", run_state="failed"),
    ]
    summary = ev.summarize("dev", "snapshot", rows, ScriptedModel(), None)
    assert summary["coverage_recorded"] == 2 and summary["coverage_incomplete_runs"] == 1
    assert summary["coverage_unresolved"] == 2 and summary["cautious_misses"] == 1
