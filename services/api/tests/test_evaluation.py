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
