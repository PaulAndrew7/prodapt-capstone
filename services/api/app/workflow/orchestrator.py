"""Runs one assessment attempt: retrieval -> analysis -> risk -> validation -> recommendation
-> final checks (plan §4.3, §7.2).

Ordinary functions in a fixed order, executed as an in-process background task. Each stage
saves a public progress event and a handoff record only after it has actually finished.
State changes take a row lock on the run, so a cancel and a publish cannot both win, and
every attempt checks for cancellation between stages and before publishing.

A restart interrupts an active attempt: `fail_interrupted_runs` marks it failed on startup
and the user starts a new run. There is no checkpoint recovery.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.contracts import (
    AgentRole,
    Assessment,
    AssessmentStatus,
    EventType,
    ExecutionInfo,
    ReviewState,
    RunState,
    SupportState,
)
from app.persistence import models as m
from app.retrieval.embeddings import Embedder
from app.workflow import analysis as analysis_stage
from app.workflow import confidence, coverage, input_guard, local_review
from app.workflow import recommendation as recommendation_stage
from app.workflow import risk as risk_stage
from app.workflow import validation as validation_stage
from app.workflow.analysis import Analysis, Answer
from app.workflow.llm import CallBudget, ModelClient, ModelError, require_model
from app.workflow.outcome import derive_status, limitations, summarize
from app.workflow.retrieval import MAX_CLAUSES, SEARCH_LIMIT, Evidence, retrieve

log = logging.getLogger("clause.workflow")

SessionFactory = Callable[[], Session]
TERMINAL = (RunState.COMPLETED, RunState.FAILED, RunState.CANCELED)
ACTIVE = (RunState.QUEUED, RunState.RUNNING, RunState.WAITING_FOR_USER)


def run_config(model: ModelClient | None, embedder: Embedder | None) -> dict[str, Any]:
    """Saved with each run so a result can be traced to its configuration."""
    return {
        "model": model.name if model else None,
        "prompts": [
            analysis_stage.PROMPT_VERSION,
            validation_stage.PROMPT_VERSION,
            recommendation_stage.PROMPT_VERSION,
        ],
        "risk_rubric": risk_stage.RUBRIC_VERSION,
        "coverage_gate": coverage.GATE_VERSION,
        "input_guard": input_guard.VERSION,
        "execution_policy": get_settings().llm_mode,
        "execution": (
            ExecutionInfo(mode="llm", reason="configured_model")
            if model
            else local_review.execution(forced=get_settings().llm_mode == "offline")
        ).model_dump(mode="json"),
        "retrieval": {
            "search_limit": SEARCH_LIMIT,
            "max_clauses": MAX_CLAUSES,
            "channels": ["lexical", "dense"] if embedder else ["lexical"],
            "embedding_model": embedder.revision if embedder else None,
        },
    }


class Canceled(Exception):
    """The run left the running state (canceled) while this attempt was working."""


@dataclass
class WorkflowDeps:
    session_factory: SessionFactory
    model: ModelClient | None
    embedder: Embedder | None
    max_calls: int
    deadline_seconds: int
    allow_fallback: bool = True
    call_timeout_seconds: float = 20


@dataclass
class Attempt:
    run_id: str
    organization_id: str
    case_id: str
    revision_id: str
    scenario: str
    as_of: str
    snapshot_id: str
    answers: list[Answer]
    resumed: bool
    execution: ExecutionInfo | None = None
    finish_local_review: bool = False
    active_stage: str = "analysis"
    started: float = field(default_factory=time.monotonic)
    parent_message: str | None = None

    def elapsed_ms(self) -> int:
        return round((time.monotonic() - self.started) * 1000)


# --- Persistence helpers ------------------------------------------------------------------


def _now() -> datetime:
    # Explicit timestamps: Postgres now() is fixed per transaction, which would tie rows
    # written together and lose their order.
    return datetime.now(UTC)


def lock_run(session: Session, run_id: str) -> m.AssessmentRun:
    return session.scalars(
        select(m.AssessmentRun).where(m.AssessmentRun.id == run_id).with_for_update()
    ).one()


def append_event(
    session: Session, run_id: str, type_: EventType, payload: dict[str, Any] | None = None
) -> m.RunEventRow:
    """Append the next event. The caller holds the run row lock, so sequences stay gap-free."""
    last = session.scalar(
        select(func.max(m.RunEventRow.sequence)).where(m.RunEventRow.run_id == run_id)
    )
    row = m.RunEventRow(
        id=m.new_id("evt"),
        run_id=run_id,
        sequence=(last or 0) + 1,
        type=type_.value,
        payload=payload or {},
        occurred_at=_now(),
    )
    session.add(row)
    session.flush()
    return row


def latest_event(session: Session, run_id: str, type_: EventType) -> m.RunEventRow | None:
    return session.scalars(
        select(m.RunEventRow)
        .where(m.RunEventRow.run_id == run_id, m.RunEventRow.type == type_.value)
        .order_by(m.RunEventRow.sequence.desc())
        .limit(1)
    ).first()


def _stage_done(
    deps: WorkflowDeps,
    attempt: Attempt,
    event: EventType,
    payload: dict[str, Any],
    handoff: tuple[AgentRole, AgentRole | str, str, str, dict[str, Any]],
) -> None:
    """Record a finished stage: its public event and its handoff to the next role."""
    sender, recipient, type_, summary, detail = handoff
    with deps.session_factory() as s:
        run = lock_run(s, attempt.run_id)
        if run.state != RunState.RUNNING:
            raise Canceled
        append_event(
            s,
            attempt.run_id,
            event,
            {
                **payload,
                "execution": attempt.execution.model_dump(mode="json")
                if attempt.execution
                else None,
            },
        )
        message_id = m.new_id("amsg")
        s.add(
            m.AgentMessageRow(
                id=message_id,
                run_id=attempt.run_id,
                sender=sender,
                recipient=recipient.value if isinstance(recipient, AgentRole) else recipient,
                type=type_,
                summary=("Local review: " + summary)
                if attempt.execution and attempt.execution.mode == "local_review"
                else summary,
                payload={
                    **detail,
                    "execution": attempt.execution.model_dump(mode="json")
                    if attempt.execution
                    else None,
                },
                causal_parent_id=attempt.parent_message,
                elapsed_ms=attempt.elapsed_ms(),
                created_at=_now(),
            )
        )
        s.commit()
    attempt.parent_message = message_id


def _plural(n: int, noun: str, plural: str | None = None) -> str:
    return f"{n} {noun if n == 1 else plural or noun + 's'}"


# --- Execution ------------------------------------------------------------------------------


def _begin(deps: WorkflowDeps, run_id: str) -> Attempt | None:
    with deps.session_factory() as s:
        run = lock_run(s, run_id)
        if run.state != RunState.QUEUED:
            return None  # a duplicate start, or canceled before it began
        if not run.config.get("execution"):
            info = (
                ExecutionInfo(mode="llm", reason="configured_model")
                if deps.model
                else local_review.execution()
            )
            run.config = {**run.config, "execution": info.model_dump(mode="json")}
        resumed = latest_event(s, run_id, EventType.RUN_RESUMED)
        answers_by_key = {}
        for event in s.scalars(
            select(m.RunEventRow)
            .where(
                m.RunEventRow.run_id == run_id, m.RunEventRow.type == EventType.RUN_RESUMED.value
            )
            .order_by(m.RunEventRow.sequence)
        ):
            for item in event.payload.get("answers", []):
                if (
                    run.config.get("execution", {}).get("mode") == "local_review"
                    and event.payload.get("execution_mode") != "local_review"
                ):
                    continue
                answer = Answer(**item)
                answers_by_key[answer.fact_key] = answer
        answers = list(answers_by_key.values())
        run.state = RunState.RUNNING
        run.started_at = run.started_at or _now()
        if resumed is None:
            append_event(s, run_id, EventType.RUN_STARTED)
        revision = s.get_one(m.ScenarioRevision, run.scenario_revision_id)
        case = s.get_one(m.Case, run.case_id)
        attempt = Attempt(
            run_id=run_id,
            organization_id=run.organization_id,
            case_id=run.case_id,
            revision_id=revision.id,
            scenario=revision.text,
            as_of=case.as_of.isoformat(),
            snapshot_id=run.snapshot_id,
            answers=answers,
            resumed=resumed is not None,
            execution=ExecutionInfo.model_validate(run.config["execution"])
            if run.config.get("execution")
            else None,
            finish_local_review=bool(run.config.get("local_review_complete")),
        )
        s.commit()
        return attempt


def _save_facts(deps: WorkflowDeps, attempt: Attempt, result: Analysis) -> None:
    with deps.session_factory() as s:
        run = lock_run(s, attempt.run_id)
        if run.state != RunState.RUNNING:
            raise Canceled
        s.execute(delete(m.Fact).where(m.Fact.scenario_revision_id == run.scenario_revision_id))
        s.add_all(
            m.Fact(
                id=f.id,
                scenario_revision_id=run.scenario_revision_id,
                key=f.key,
                label=f.label,
                value=f.value,
                origin=f.origin,
                confirmed=f.confirmed,
                source_message_id=f.source_message_id,
            )
            for f in result.facts
        )
        s.commit()


def _usage(budget: CallBudget | None) -> dict[str, Any]:
    return (
        budget.usage()
        if budget
        else {
            "model": None,
            "served_model": None,
            "model_calls": 0,
            "model_requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
    )


def _ask(deps: WorkflowDeps, attempt: Attempt, result: Analysis, budget: CallBudget | None) -> None:
    count = (
        "one question" if len(result.questions) == 1 else _plural(len(result.questions), "question")
    )
    with deps.session_factory() as s:
        run = lock_run(s, attempt.run_id)
        if run.state != RunState.RUNNING:
            raise Canceled
        run.state = RunState.WAITING_FOR_USER
        run.usage = {**run.usage, "waiting_attempt": _usage(budget)}
        s.add(
            m.CaseMessage(
                id=m.new_id("msg"),
                case_id=attempt.case_id,
                role="assistant",
                created_at=_now(),
                text=(
                    f"Local review has {count} source-linked checks in this batch. "
                    "Confirm each disposition, or finish with remaining checks unknown."
                    if attempt.execution and attempt.execution.mode == "local_review"
                    else f"Some facts that decide this case are missing. I have {count} before "
                    "I finish the assessment."
                ),
            )
        )
        append_event(
            s,
            attempt.run_id,
            EventType.CLARIFICATION_REQUIRED,
            {"questions": [q.model_dump(mode="json") for q in result.questions]},
        )
        s.get_one(m.Case, attempt.case_id).updated_at = _now()
        s.commit()


def _publish(
    deps: WorkflowDeps, attempt: Attempt, assessment: Assessment, budget: CallBudget | None
) -> None:
    with deps.session_factory() as s:
        run = lock_run(s, attempt.run_id)
        if run.state != RunState.RUNNING:
            raise Canceled  # canceled while the last stage ran: publish nothing
        run.assessment = assessment.model_dump(mode="json")
        run.result_status = assessment.status
        run.state = RunState.COMPLETED
        run.finished_at = _now()
        run.usage = {**run.usage, "final_attempt": _usage(budget), "run_ms": attempt.elapsed_ms()}
        case = s.get_one(m.Case, attempt.case_id)
        case.scope = assessment.scope
        case.updated_at = _now()
        append_event(s, attempt.run_id, EventType.RUN_COMPLETED, {"status": assessment.status})
        s.commit()


def fail_run(
    factory: SessionFactory, run_id: str, code: str, message: str, retryable: bool
) -> None:
    with factory() as s:
        run = lock_run(s, run_id)
        if run.state in TERMINAL:
            return
        run.state = RunState.FAILED
        run.error = {"code": code, "message": message, "retryable": retryable}
        run.finished_at = _now()
        append_event(
            s,
            run_id,
            EventType.RUN_FAILED,
            {"code": code, "message": message, "retryable": retryable},
        )
        s.get_one(m.Case, run.case_id).updated_at = _now()
        s.commit()


def _stages(deps: WorkflowDeps, attempt: Attempt, allow_clarification: bool) -> None:
    if refusal := input_guard.screen(attempt.scenario):
        fail_run(deps.session_factory, attempt.run_id, refusal.code, refusal.message, False)
        return
    # Clarification text is user input too. Short factual answers can rely on the
    # scenario for context, but must not redirect the model on a resumed attempt.
    for answer in attempt.answers:
        if answer.answer and (
            refusal := input_guard.screen(answer.answer, allow_short_answer=True)
        ):
            fail_run(deps.session_factory, attempt.run_id, refusal.code, refusal.message, False)
            return
    # 1. Retrieval: local search, no model call.
    with deps.session_factory() as s:
        evidence = retrieve(
            s,
            attempt.organization_id,
            snapshot_id=attempt.snapshot_id,
            as_of=datetime.fromisoformat(attempt.as_of).date(),
            query=attempt.scenario,
            embedder=deps.embedder,
        )
    if refusal := input_guard.check_evidence(attempt.scenario, evidence):
        fail_run(deps.session_factory, attempt.run_id, refusal.code, refusal.message, False)
        return
    clauses = evidence.by_id()
    policies = evidence.policies()
    _stage_done(
        deps,
        attempt,
        EventType.RETRIEVAL_COMPLETED,
        {"clauses": len(evidence.clauses), "policies": len(policies)},
        (
            AgentRole.RETRIEVAL,
            AgentRole.ANALYSIS,
            "evidence.bundle",
            f"Retrieved {_plural(len(evidence.clauses), 'clause')} from "
            f"{_plural(len(policies), 'policy', 'policies')}",
            {"clause_ids": list(clauses), "search_hits": evidence.search_hits},
        ),
    )

    local = (
        deps.allow_fallback
        and attempt.execution is not None
        and attempt.execution.mode == "local_review"
    )
    if deps.model is None and deps.allow_fallback and not local:
        # A provider can disappear while a model run waits for clarification.
        # Persist the switch and do not treat earlier model answers as local attestations.
        local = True
        attempt.execution = local_review.execution(forced=get_settings().llm_mode == "offline")
        attempt.answers = []
        with deps.session_factory() as s:
            run = lock_run(s, attempt.run_id)
            if run.state != RunState.RUNNING:
                raise Canceled
            run.config = {**run.config, "execution": attempt.execution.model_dump(mode="json")}
            append_event(
                s, run.id, EventType.RUN_FALLBACK, attempt.execution.model_dump(mode="json")
            )
            s.commit()
    if local:
        _review_stages(deps, attempt, evidence, None, allow_clarification, local=True)
        return
    budget = CallBudget(
        require_model(deps.model),
        deps.max_calls,
        deps.deadline_seconds,
        call_timeout_seconds=deps.call_timeout_seconds,
    )
    try:
        _review_stages(deps, attempt, evidence, budget, allow_clarification, local=False)
    except ModelError as exc:
        if not deps.allow_fallback:
            raise
        attempt.execution = local_review.execution(error_code=exc.code, stage=attempt.active_stage)
        # Model clarification answers were not explicit local dispositions.
        attempt.answers = []
        with deps.session_factory() as s:
            run = lock_run(s, attempt.run_id)
            if run.state != RunState.RUNNING:
                raise Canceled from exc
            run.config = {**run.config, "execution": attempt.execution.model_dump(mode="json")}
            run.usage = {**run.usage, "fallback_attempt": budget.usage()}
            append_event(
                s, run.id, EventType.RUN_FALLBACK, attempt.execution.model_dump(mode="json")
            )
            s.commit()
        log.warning(
            "Run %s switched to local review at %s (%s)",
            attempt.run_id,
            attempt.active_stage,
            attempt.execution.error_code,
        )
        _review_stages(deps, attempt, evidence, None, allow_clarification, local=True)


def _review_stages(
    deps: WorkflowDeps,
    attempt: Attempt,
    evidence: Evidence,
    budget: CallBudget | None,
    allow_clarification: bool,
    *,
    local: bool,
) -> None:
    clauses = evidence.by_id()
    attempt.active_stage = "analysis"
    if local:
        result = local_review.analyze(
            evidence, attempt.answers, ask=allow_clarification and not attempt.finish_local_review
        )
    elif evidence.clauses:
        assert budget is not None
        result = analysis_stage.analyze(
            budget,
            scenario=attempt.scenario,
            as_of=attempt.as_of,
            answers=attempt.answers,
            evidence=evidence,
            allow_questions=allow_clarification and not attempt.resumed,
        )
    else:
        result = Analysis(False, [], [], {}, [])
    _save_facts(deps, attempt, result)
    unknown = sum(1 for f in result.facts if f.value is None)
    _stage_done(
        deps,
        attempt,
        EventType.ANALYSIS_COMPLETED,
        {
            "findings": len(result.findings),
            "unknown_facts": unknown,
            "questions": len(result.questions),
        },
        (
            AgentRole.ANALYSIS,
            AgentRole.RISK,
            "findings.proposed",
            f"Proposed {_plural(len(result.findings), 'finding')}; "
            f"{_plural(unknown, 'fact')} unknown",
            {
                "findings": {f.id: f.status.value for f in result.findings},
                "in_scope": result.in_scope,
            },
        ),
    )
    if result.questions:
        _ask(deps, attempt, result, budget)
        return

    # 3. Risk: the documented rubric, no model call.
    risks = risk_stage.assess(result.findings, clauses)
    _stage_done(
        deps,
        attempt,
        EventType.RISK_COMPLETED,
        {"risks": len(risks)},
        (
            AgentRole.RISK,
            AgentRole.VALIDATION,
            "risks.scored",
            f"Scored {_plural(len(risks), 'risk')} with {risk_stage.RUBRIC_VERSION}",
            {"risks": {r.id: r.severity.value for r in risks}},
        ),
    )

    # 4. Validation: code checks, then one model call. Risk is recomputed afterwards.
    attempt.active_stage = "validation"
    if local:
        checked = local_review.validate(result, evidence)
    else:
        assert budget is not None
        checked = validation_stage.validate(
            budget,
            scenario=attempt.scenario,
            answers=attempt.answers,
            facts=result.facts,
            findings=result.findings,
            proposed=result.proposed_evidence,
            evidence=evidence,
        )
    findings = checked.findings
    coverage_report = coverage.inspect(evidence, findings)
    risks = risk_stage.assess(findings, clauses)
    confirmed = checked.count(SupportState.VALIDATED)
    _stage_done(
        deps,
        attempt,
        EventType.VALIDATION_COMPLETED,
        {
            "validated": confirmed,
            "unsupported": checked.count(SupportState.UNSUPPORTED),
            "contradicted": checked.count(SupportState.CONTRADICTED),
            "downgraded": checked.downgraded,
            "citations_proposed": checked.proposed_references,
            "citation_problems": checked.invalid_references + checked.quote_mismatches,
            "coverage_candidates": coverage_report.candidate_count,
            "coverage_accounted": coverage_report.accounted_count,
            "coverage_unresolved": len(coverage_report.unresolved_clause_ids),
        },
        (
            AgentRole.VALIDATION,
            AgentRole.RECOMMENDATION,
            "findings.validated",
            f"Confirmed {confirmed} of {_plural(len(findings), 'finding')} against the cited text; "
            f"accounted for {coverage_report.accounted_count} of "
            f"{coverage_report.candidate_count} retrieved candidates",
            {
                "support": {f.id: f.support.value for f in findings},
                "notes": checked.notes,
                "coverage": coverage_report.model_dump(mode="json"),
            },
        ),
    )

    # 5. Recommendation: one model call on validated gaps.
    attempt.active_stage = "recommendation"
    if local:
        actions, dropped = local_review.recommend(checked)
    else:
        assert budget is not None
        actions, dropped = recommendation_stage.recommend(
            budget, scenario=attempt.scenario, findings=findings, citations=checked.citations
        )
    _stage_done(
        deps,
        attempt,
        EventType.RECOMMENDATION_COMPLETED,
        {"actions": len(actions)},
        (
            AgentRole.RECOMMENDATION,
            "gate",
            "actions.proposed",
            f"Proposed {_plural(len(actions), 'action')} linked to validated findings",
            {"actions": {a.id: a.finding_ids for a in actions}, "dropped": dropped},
        ),
    )

    # 6. Final checks: the contract validates every field; the rules decide the status.
    status = derive_status(findings, coverage_report)
    if local and not findings:
        status = AssessmentStatus.INSUFFICIENT_INFORMATION
    findings = [
        f.model_copy(
            update={
                "confidence": None
                if local
                else confidence.score_finding(
                    f, checked.citations, result.facts, evidence, verified=checked.verified_quotes
                )
            }
        )
        for f in findings
    ]
    cited_policies = sorted(
        {clauses[c.clause_id].policy_title for c in checked.citations if c.clause_id in clauses}
    )
    assessment = Assessment(
        run_id=attempt.run_id,
        case_revision_id=attempt.revision_id,
        policy_snapshot_id=attempt.snapshot_id,
        as_of=datetime.fromisoformat(attempt.as_of).date(),
        status=status,
        scope="Kestrel Mutual demo corpus"
        + (f": {', '.join(cited_policies)}" if cited_policies else ""),
        summary=local_review.summary(status, findings)
        if local
        else summarize(status, findings, coverage_report),
        findings=findings,
        citations=checked.citations,
        risks=risks,
        recommendations=actions,
        limitations=limitations(
            snapshot_id=attempt.snapshot_id,
            as_of=attempt.as_of,
            findings=findings,
            quote_mismatches=checked.quote_mismatches,
            invalid_references=checked.invalid_references,
            dropped_actions=dropped,
            unanswered=sum(1 for a in attempt.answers if a.answer is None),
            coverage=coverage_report,
        )
        + ([local_review.LIMITATION] if local else []),
        review_state=ReviewState.UNREVIEWED,
        confidence=None
        if local
        else confidence.score_assessment(status, findings, evidence, coverage_report),
        coverage=coverage_report,
        execution=attempt.execution,
    )
    _publish(deps, attempt, assessment, budget)


def execute_run(deps: WorkflowDeps, run_id: str, *, allow_clarification: bool = True) -> None:
    """Run one attempt. Never raises: failures are recorded on the run."""
    try:
        attempt = _begin(deps, run_id)
        if attempt is None:
            return
        _stages(deps, attempt, allow_clarification)
    except Canceled:
        log.info("Run %s was canceled; the attempt stopped without publishing", run_id)
    except ModelError as exc:
        log.warning("Run %s failed: %s (%s)", run_id, exc.code, exc.message)
        fail_run(deps.session_factory, run_id, exc.code, exc.message, exc.retryable)
    except Exception:
        log.exception("Run %s failed with an internal error", run_id)
        fail_run(
            deps.session_factory,
            run_id,
            "internal_error",
            "The assessment stopped because of an internal error. Start a new run.",
            True,
        )


def fail_interrupted_runs(factory: SessionFactory) -> int:
    """On startup, fail runs whose attempt died with the previous process."""
    with factory() as s:
        ids = s.scalars(
            select(m.AssessmentRun.id).where(
                m.AssessmentRun.state.in_([RunState.QUEUED, RunState.RUNNING])
            )
        ).all()
    for run_id in ids:
        fail_run(
            factory,
            run_id,
            "interrupted",
            "The server restarted while this run was in progress. Start a new run.",
            True,
        )
    return len(ids)
