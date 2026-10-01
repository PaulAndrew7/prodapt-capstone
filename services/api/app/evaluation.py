"""Evaluation (plan §13; F14): one script, the same workflow, measured results.

For each scenario in data/evaluation/<split>/scenarios.json:
- Recall@10: the labelled clauses found in the top ten search results, divided by the labelled
  clauses (hybrid search, and keyword-only for comparison). No-evidence cases are N/A.
- With a model configured, the full assessment runs through the normal records and workflow
  with clarification turned off, so unstated facts stay unknown. It then scores the final
  status against the acceptable labels, false-compliant results, citation validity
  (proposed citations that resolved to a retrieved clause with a matching quote),
  requirement labels matched, and run time.
Evidence support needs a person: the raw file lists every decisive claim with its quotes for
manual review. Answer keys are read here only; they never reach retrieval or prompts.
"""

import hashlib
import json
import statistics
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import REPO_ROOT, get_settings
from app.domain.contracts import AssessmentStatus, EventType, RunState, SearchRequest
from app.persistence import models as m
from app.persistence.db import new_session
from app.retrieval.embeddings import Embedder
from app.retrieval.search import latest_snapshot_id, search
from app.seed import DEMO_ADMIN_ID, DEMO_ORG_ID
from app.workflow import records
from app.workflow.llm import ModelClient
from app.workflow.orchestrator import WorkflowDeps, execute_run, latest_event, run_config
from app.workflow.retrieval import retrieve

EVAL_DIR = REPO_ROOT / "data" / "evaluation"
DOCS_DIR = REPO_ROOT / "docs" / "evaluation"


@dataclass
class ScenarioResult:
    id: str
    category: str
    acceptable_status: list[str]
    expected_clauses: list[str]
    top10_hybrid: list[str]
    recall_hybrid: float | None
    recall_lexical: float | None
    recall_bundle: float | None
    # Filled only when a model ran the assessment.
    run_state: str | None = None
    status: str | None = None
    status_ok: bool | None = None
    false_compliant: bool | None = None
    unjustified_compliant: bool | None = None
    coverage_candidates: int | None = None
    coverage_accounted: int | None = None
    coverage_unresolved: int | None = None
    requirements_matched: int | None = None
    requirements_labelled: int | None = None
    citations_proposed: int | None = None
    citation_problems: int | None = None
    run_ms: int | None = None
    served_model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None
    decisive_claims: list[dict[str, Any]] = field(default_factory=list)
    # Evidence scores (app/workflow/confidence.py) for the result and each labelled finding.
    confidence_score: int | None = None
    confidence_band: str | None = None
    finding_bands: list[dict[str, Any]] = field(default_factory=list)


def load_scenarios(split: str) -> list[dict[str, Any]]:
    if split not in {"dev", "test"}:
        raise ValueError("Evaluation split must be dev or test")
    path = EVAL_DIR / split / "scenarios.json"
    if not path.exists():
        raise FileNotFoundError(f"{path.relative_to(REPO_ROOT)} does not exist yet")
    data: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return data


def select_scenarios(split: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Validate before database setup or model calls; never evaluate disputed labels."""
    if limit is not None and limit <= 0:
        raise ValueError("Evaluation limit must be positive")
    eligible = [s for s in load_scenarios(split) if s.get("review") != "disputed"]
    if split == "test" and any(s.get("review") != "reviewed" for s in eligible):
        raise ValueError("Held-out labels need owner review and freeze before evaluation")
    selected = eligible[:limit]
    if not selected:
        raise ValueError("No eligible evaluation scenarios remain")
    return selected


def _recall(expected: set[str], found: list[str]) -> float | None:
    return len(expected & set(found)) / len(expected) if expected else None


def _top10(
    session: Session, scenario: dict[str, Any], snapshot_id: str, embedder: Embedder | None
) -> list[str]:
    result = search(
        session,
        DEMO_ORG_ID,
        SearchRequest(
            question=scenario["scenario"], as_of=date.fromisoformat(scenario["as_of"]), limit=10
        ),
        embedder,
        snapshot_id=snapshot_id,
    )
    return [h.clause.id for h in result.hits]


def declined_status(error: dict[str, Any] | None) -> str | None:
    """The result a run without an assessment gave the user, if it gave one.

    The input check (app/workflow/input_guard.py) stops an unrelated request before any
    assessment and tells the user it could not connect the request to the policies: that is
    the out-of-scope answer, so it is scored as one. Redirect refusals and every other
    failure produced no result and count as wrong.
    """
    if error and error.get("code") == "request_out_of_scope":
        return AssessmentStatus.OUT_OF_SCOPE.value
    return None


def _assess(
    deps: WorkflowDeps, scenario: dict[str, Any], snapshot_id: str, result: ScenarioResult
) -> None:
    with new_session() as s:
        case = records.create_case(
            s,
            organization_id=DEMO_ORG_ID,
            owner_id=DEMO_ADMIN_ID,
            text=scenario["scenario"],
            business_area="Evaluation",
            as_of=date.fromisoformat(scenario["as_of"]),
        )
        run = records.create_run(
            s,
            case,
            created_by=DEMO_ADMIN_ID,
            snapshot_id=snapshot_id,
            idempotency_key=f"eval-{scenario['id']}-{datetime.now(UTC).timestamp()}",
            config=run_config(deps.model, deps.embedder),
            budget={"max_model_calls": deps.max_calls, "deadline_seconds": deps.deadline_seconds},
        )
        s.commit()
        run_id = run.id
    execute_run(deps, run_id, allow_clarification=False)

    with new_session() as s:
        run = s.get_one(m.AssessmentRun, run_id)
        result.run_state = run.state.value
        result.run_ms = run.usage.get("run_ms")
        usage = run.usage.get("final_attempt") or {}
        result.served_model = usage.get("served_model")
        result.input_tokens = usage.get("input_tokens")
        result.output_tokens = usage.get("output_tokens")
        if run.error:
            result.error = f"{run.error['code']}: {run.error['message']}"
        validation = latest_event(s, run_id, EventType.VALIDATION_COMPLETED)
        if validation:
            result.citations_proposed = validation.payload.get("citations_proposed", 0)
            result.citation_problems = validation.payload.get("citation_problems", 0)
        if run.state != RunState.COMPLETED or run.assessment is None:
            result.status = declined_status(run.error)
            result.status_ok = result.status in scenario["acceptable_status"]
            return
        a = run.assessment
    result.status = a["status"]
    result.status_ok = a["status"] in scenario["acceptable_status"]
    result.false_compliant = (
        "non_compliant" in scenario["acceptable_status"]
        and a["status"] == AssessmentStatus.COMPLIANT_WITHIN_SCOPE
    )
    result.unjustified_compliant = (
        a["status"] == AssessmentStatus.COMPLIANT_WITHIN_SCOPE
        and AssessmentStatus.COMPLIANT_WITHIN_SCOPE not in scenario["acceptable_status"]
    )
    if a.get("coverage"):
        result.coverage_candidates = a["coverage"]["candidate_count"]
        result.coverage_accounted = a["coverage"]["accounted_count"]
        result.coverage_unresolved = len(a["coverage"]["unresolved_clause_ids"])
    predicted = {f["requirement_id"]: f["status"] for f in a["findings"]}
    labels: dict[str, str] = scenario["requirements"]
    result.requirements_labelled = len(labels)
    result.requirements_matched = sum(predicted.get(cid) == want for cid, want in labels.items())
    if a.get("confidence"):
        result.confidence_score = a["confidence"]["score"]
        result.confidence_band = a["confidence"]["band"]
    result.finding_bands = [
        {
            "requirement_id": f["requirement_id"],
            "band": f["confidence"]["band"],
            "score": f["confidence"]["score"],
            "matched": f["status"] == labels[f["requirement_id"]],
        }
        for f in a["findings"]
        if f.get("confidence") and f["requirement_id"] in labels
    ]
    result.decisive_claims = _decisive_claims(a)


def _decisive_claims(a: dict[str, Any]) -> list[dict[str, Any]]:
    quotes = {c["id"]: f"{c['clause_id']}: {c['quote']}" for c in a["citations"]}
    return [
        {
            "requirement": f["requirement_id"],
            "status": f["status"],
            "support": f["support"],
            "rationale": f["rationale"],
            "citations": [quotes[c] for c in f["citation_ids"]],
            "supported_by_reviewer": None,
        }
        for f in a["findings"]
        if f["support"] == "validated" and f["status"] in ("violated", "met", "conflict")
    ]


def evaluate(
    split: str, *, model: ModelClient | None, embedder: Embedder | None, limit: int | None = None
) -> tuple[dict[str, Any], list[ScenarioResult]]:
    scenarios = select_scenarios(split, limit)
    settings = get_settings()
    with new_session() as s:
        snapshot_id = latest_snapshot_id(s, DEMO_ORG_ID)
    if snapshot_id is None:
        raise RuntimeError("The evaluation database has no snapshot; seed it first")
    deps = WorkflowDeps(
        new_session, model, embedder, settings.run_max_model_calls, settings.run_deadline_seconds
    )
    results: list[ScenarioResult] = []
    for sc in scenarios:
        expected = set(sc["requirements"])
        with new_session() as s:
            hybrid = _top10(s, sc, snapshot_id, embedder)
            lexical = _top10(s, sc, snapshot_id, None) if embedder else hybrid
            bundle = retrieve(
                s,
                DEMO_ORG_ID,
                snapshot_id=snapshot_id,
                as_of=date.fromisoformat(sc["as_of"]),
                query=sc["scenario"],
                embedder=embedder,
            )
        result = ScenarioResult(
            id=sc["id"],
            category=sc["category"],
            acceptable_status=sc["acceptable_status"],
            expected_clauses=sorted(expected),
            top10_hybrid=hybrid,
            recall_hybrid=_recall(expected, hybrid),
            recall_lexical=_recall(expected, lexical),
            recall_bundle=_recall(expected, [c.id for c in bundle.clauses]),
            requirements_labelled=len(sc["requirements"]),
        )
        if model is not None:
            _assess(deps, sc, snapshot_id, result)
        results.append(result)
        print(f"{sc['id']}: recall={result.recall_hybrid} status={result.status}", flush=True)
    return summarize(split, snapshot_id, results, model, embedder), results


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return round(statistics.mean(present), 3) if present else None


def summarize(
    split: str,
    snapshot_id: str,
    results: list[ScenarioResult],
    model: ModelClient | None,
    embedder: Embedder | None,
) -> dict[str, Any]:
    answerable = [r for r in results if r.recall_hybrid is not None]
    summary: dict[str, Any] = {
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "split": split,
        "scenarios": len(results),
        "reviewed_labels": sum(
            1
            for s in load_scenarios(split)
            if s["id"] in {r.id for r in results} and s.get("review") == "reviewed"
        ),
        "excluded_disputed": sum(s.get("review") == "disputed" for s in load_scenarios(split)),
        "scenario_sha256": hashlib.sha256(
            (EVAL_DIR / split / "scenarios.json").read_bytes()
        ).hexdigest(),
        "corpus_manifest_sha256": hashlib.sha256(
            (REPO_ROOT / "data" / "demo" / "manifest.json").read_bytes()
        ).hexdigest(),
        "retrieval_mode": "hybrid"
        if embedder is not None
        else "keyword only (embeddings disabled)",
        "snapshot_id": snapshot_id,
        "configuration": run_config(model, embedder),
        "recall_at_10_hybrid": _mean([r.recall_hybrid for r in answerable]),
        "recall_at_10_lexical": _mean([r.recall_lexical for r in answerable]),
        "recall_bundle": _mean([r.recall_bundle for r in answerable]),
        "answerable": len(answerable),
        "assessed": model is not None,
    }
    if model is None:
        return summary
    completed = [r for r in results if r.run_state == RunState.COMPLETED.value]
    labelled_non_compliant = [r for r in results if "non_compliant" in r.acceptable_status]
    no_clearance = [
        r for r in results if AssessmentStatus.COMPLIANT_WITHIN_SCOPE not in r.acceptable_status
    ]
    run_times = [r.run_ms for r in completed if r.run_ms is not None]
    proposed = sum(r.citations_proposed or 0 for r in results)
    problems = sum(r.citation_problems or 0 for r in results)
    summary.update(
        {
            "completed": len(completed),
            "failed": len(results) - len(completed),
            "status_correct": sum(1 for r in results if r.status_ok),
            "false_compliant": sum(1 for r in results if r.false_compliant),
            "labelled_non_compliant": len(labelled_non_compliant),
            "unjustified_compliant": sum(
                r.status == AssessmentStatus.COMPLIANT_WITHIN_SCOPE
                for r in no_clearance
                if r.run_state == RunState.COMPLETED.value
            ),
            "labelled_no_clearance": len(no_clearance),
            "coverage_recorded": sum(r.coverage_candidates is not None for r in results),
            "coverage_unresolved": sum(r.coverage_unresolved or 0 for r in results),
            "coverage_incomplete_runs": sum(bool(r.coverage_unresolved) for r in results),
            "cautious_misses": sum(
                r.status == AssessmentStatus.INSUFFICIENT_INFORMATION
                and AssessmentStatus.COMPLIANT_WITHIN_SCOPE in r.acceptable_status
                and AssessmentStatus.INSUFFICIENT_INFORMATION not in r.acceptable_status
                for r in completed
            ),
            "citations_proposed": proposed,
            "citations_valid": proposed - problems,
            "requirements_matched": sum(r.requirements_matched or 0 for r in results),
            "requirements_labelled": sum(r.requirements_labelled or 0 for r in results),
            "median_run_seconds": round(statistics.median(run_times) / 1000, 1)
            if run_times
            else None,
            "served_models": sorted({r.served_model for r in results if r.served_model}),
            "input_tokens": sum(r.input_tokens or 0 for r in results),
            "output_tokens": sum(r.output_tokens or 0 for r in results),
            "by_band": _by_band(results),
        }
    )
    return summary


BANDS = ("high", "medium", "low")


def _by_band(results: list[ScenarioResult]) -> dict[str, dict[str, int]]:
    """Measured accuracy per confidence band: results and labelled findings."""
    out = {
        b: {"results": 0, "results_correct": 0, "findings": 0, "findings_matched": 0} for b in BANDS
    }
    for r in results:
        if r.confidence_band in out:
            out[r.confidence_band]["results"] += 1
            out[r.confidence_band]["results_correct"] += bool(r.status_ok)
        for f in r.finding_bands:
            out[f["band"]]["findings"] += 1
            out[f["band"]]["findings_matched"] += bool(f["matched"])
    return out


def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({n / d:.0%})" if d else "n/a"


def _cell(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "&#124;")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def write_report(summary: dict[str, Any], results: list[ScenarioResult]) -> tuple[Path, Path]:
    raw_dir = DOCS_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = summary["date"][:10]
    raw = raw_dir / f"{summary['split']}-{stamp}-{uuid.uuid4().hex}.json"
    with raw.open("x", encoding="utf-8", newline="\n") as output:
        output.write(
            json.dumps({"summary": summary, "results": [asdict(r) for r in results]}, indent=2)
            + "\n"
        )
    cfg = summary["configuration"]
    lines = [
        "# Evaluation results",
        "",
        "> Generated by `python -m app.cli evaluate`. Numbers are measured on the fictional "
        "Kestrel Mutual corpus and a small hand-labelled scenario set; they are not a claim "
        "about real policies or general accuracy.",
        "",
        f"- Date: {summary['date']}",
        f"- Split: `{summary['split']}` ({summary['scenarios']} scenarios, "
        f"{summary['reviewed_labels']} with reviewed labels)",
        f"- Policy snapshot: `{summary['snapshot_id']}`",
        f"- Excluded disputed labels: {summary['excluded_disputed']}",
        f"- Scenario file SHA-256: `{summary['scenario_sha256']}`",
        f"- Corpus manifest SHA-256: `{summary['corpus_manifest_sha256']}`",
        f"- Model: `{cfg['model'] or 'none configured'}`; prompts: "
        + ", ".join(f"`{p}`" for p in cfg["prompts"]),
        f"- Coverage gate: `{cfg['coverage_gate']}` (retrieved candidates only)",
        f"- Retrieval: {', '.join(cfg['retrieval']['channels'])} "
        f"(embeddings `{cfg['retrieval']['embedding_model']}`), search limit "
        f"{cfg['retrieval']['search_limit']}, evidence bundle up to "
        f"{cfg['retrieval']['max_clauses']} clauses; risk rubric `{cfg['risk_rubric']}`",
        f"- Raw results: [{raw.name}]({raw.relative_to(DOCS_DIR).as_posix()})",
        "",
        "## Measurements",
        "",
        "| Measurement | Result | Definition |",
        "|---|---|---|",
        f"| Recall@10, {summary['retrieval_mode']} | {summary['recall_at_10_hybrid']} | "
        "Mean share of labelled clauses "
        f"in the top ten search results, over {summary['answerable']} scenarios with labelled "
        "clauses |",
        f"| Recall@10, keyword only | {summary['recall_at_10_lexical']} | Same, full-text "
        "channel alone |",
        f"| Evidence bundle recall | {summary['recall_bundle']} | Share of labelled clauses in "
        "the bundle the analysis stage reads (top ten hits plus cited, exception and "
        "definition clauses) |",
    ]
    if summary["assessed"]:
        lines += [
            f"| Final-status accuracy | {_pct(summary['status_correct'], summary['scenarios'])} "
            "| Result is one of the acceptable labels; a request the input check declines as "
            "unrelated counts as out_of_scope, other failed runs count as wrong |",
            f"| False-compliant results | {summary['false_compliant']} of "
            f"{summary['labelled_non_compliant']} | Labelled non-compliant, predicted "
            "compliant |",
            f"| Unjustified compliant results | {summary['unjustified_compliant']} of "
            f"{summary['labelled_no_clearance']} | Predicted compliant when compliance is absent "
            "from the acceptable labels, including unknown/conflict cases; failed runs remain "
            "in the denominator |",
            f"| Cautious misses | {summary['cautious_misses']} | Predicted insufficient "
            "information when compliance is acceptable and insufficiency is not |",
            f"| Incomplete coverage runs | {summary['coverage_incomplete_runs']} of "
            f"{summary['coverage_recorded']} | Completed assessments with unresolved retrieved "
            "candidates; not a measure of full-policy recall |",
            f"| Unresolved candidates | {summary['coverage_unresolved']} | Total unresolved "
            "candidates across recorded assessments |",
            "| Citation validity | "
            f"{_pct(summary['citations_valid'], summary['citations_proposed'])} | Proposed "
            "citations that named a retrieved clause and quoted it exactly |",
            f"| Requirement labels matched | "
            f"{_pct(summary['requirements_matched'], summary['requirements_labelled'])} | "
            "Labelled clause statuses reproduced by a finding; failed runs count as unmatched |",
            f"| Completed / failed runs | {summary['completed']} / {summary['failed']} | |",
            f"| Median run time | {summary['median_run_seconds']} s | Completed runs |",
            f"| Tokens in / out | {summary['input_tokens']} / {summary['output_tokens']} | "
            "As reported by the model provider, all runs; served model "
            f"{', '.join(f'`{m}`' for m in summary['served_models']) or 'not reported'} |",
            "| Evidence support | pending manual review | Decisive claims are listed in the "
            "raw file for a person to mark |",
            "",
            "### Accuracy by confidence band",
            "",
            "Each result and finding carries an evidence score computed in code "
            "(`app/workflow/confidence.py`; high >= 80, medium >= 50). This table is the "
            "measured check of that score: how often each band was right on this split.",
            "",
            "| Band | Results correct | Labelled findings matched |",
            "|---|---|---|",
            *(
                f"| {band.capitalize()} | "
                f"{_pct(c['results_correct'], c['results'])} | "
                f"{_pct(c['findings_matched'], c['findings'])} |"
                for band, c in summary["by_band"].items()
            ),
        ]
    else:
        lines += [
            "",
            "No language model was configured, so only retrieval was measured. Assessment "
            "measurements (status accuracy, false-compliant results, citation validity, run "
            "time) need `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY`.",
        ]
    lines += ["", "## Per scenario", ""]
    header = "| Scenario | Category | Recall@10 | Expected | Result | Confidence |"
    lines += [header, "|---|---|---|---|---|---|"]
    for r in results:
        recall = "n/a" if r.recall_hybrid is None else f"{r.recall_hybrid:.2f}"
        if r.run_state is None:
            outcome = "not run"
        elif r.status and r.run_state != RunState.COMPLETED.value:
            outcome = f"{r.status} (declined by the input check)"
        else:
            outcome = r.status or r.error or r.run_state
        if r.run_state is not None:
            outcome += " ✓" if r.status_ok else " ✗"
        lines.append(
            "| "
            + " | ".join(
                _cell(v)
                for v in (
                    r.id,
                    r.category,
                    recall,
                    ", ".join(r.acceptable_status),
                    outcome,
                    "n/a"
                    if r.confidence_score is None
                    else f"{r.confidence_score} {r.confidence_band}",
                )
            )
            + " |"
        )
    missed = [r for r in results if r.recall_hybrid is not None and r.recall_hybrid < 1]
    if missed:
        lines += ["", "### Labelled clauses missing from the top ten", ""]
        for r in missed:
            absent = sorted(set(r.expected_clauses) - set(r.top10_hybrid))
            bundle = "" if r.recall_bundle is None else f" (bundle recall {r.recall_bundle:.2f})"
            lines.append(f"- {r.id}: {', '.join(absent)}{bundle}")
    lines += [
        "",
        "## Failures and limits",
        "",
        "The written analysis of real failures lives in [analysis.md](analysis.md), so "
        "regenerating this file does not erase it. A small set with no observed "
        "false-compliant results is not proof of correctness, and a valid citation shows the "
        "quoted text exists, not that the interpretation is right.",
        "",
    ]
    report = DOCS_DIR / f"results-{summary['split']}.md"
    report.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return report, raw
