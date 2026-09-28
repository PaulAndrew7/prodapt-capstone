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

from app.domain.contracts import (
    AgentRole,
    Assessment,
    EventType,
    ReviewState,
    RunState,
    SupportState,
)
from app.persistence import models as m
from app.retrieval.embeddings import Embedder
from app.workflow import analysis as analysis_stage
from app.workflow import recommendation as recommendation_stage
from app.workflow import risk as risk_stage
from app.workflow import validation as validation_stage
from app.workflow.analysis import Analysis, Answer
from app.workflow.llm import CallBudget, ModelClient, ModelError, require_model
from app.workflow.outcome import derive_status, limitations, summarize
from app.workflow.retrieval import MAX_CLAUSES, SEARCH_LIMIT, retrieve

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
        append_event(s, attempt.run_id, event, payload)
        message_id = m.new_id("amsg")
        s.add(
            m.AgentMessageRow(
                id=message_id,
                run_id=attempt.run_id,
                sender=sender,
                recipient=recipient.value if isinstance(recipient, AgentRole) else recipient,
                type=type_,
                summary=summary,
                payload=detail,
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
        resumed = latest_event(s, run_id, EventType.RUN_RESUMED)
        answers = [Answer(**a) for a in (resumed.payload.get("answers", []) if resumed else [])]
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


def _ask(deps: WorkflowDeps, attempt: Attempt, result: Analysis, budget: CallBudget) -> None:
    count = (
        "one question" if len(result.questions) == 1 else _plural(len(result.questions), "question")
    )
    with deps.session_factory() as s:
        run = lock_run(s, attempt.run_id)
        if run.state != RunState.RUNNING:
            raise Canceled
        run.state = RunState.WAITING_FOR_USER
        run.usage = {**run.usage, "waiting_attempt": budget.usage()}
        s.add(
            m.CaseMessage(
                id=m.new_id("msg"),
                case_id=attempt.case_id,
                role="assistant",
                created_at=_now(),
                text=f"Some facts that decide this case are missing. I have {count} before "
                "I finish the assessment.",
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
    deps: WorkflowDeps, attempt: Attempt, assessment: Assessment, budget: CallBudget
) -> None:
    with deps.session_factory() as s:
        run = lock_run(s, attempt.run_id)
        if run.state != RunState.RUNNING:
            raise Canceled  # canceled while the last stage ran: publish nothing
        run.assessment = assessment.model_dump(mode="json")
        run.result_status = assessment.status
        run.state = RunState.COMPLETED
        run.finished_at = _now()
        run.usage = {**run.usage, "final_attempt": budget.usage(), "run_ms": attempt.elapsed_ms()}
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
    budget = CallBudget(require_model(deps.model), deps.max_calls, deps.deadline_seconds)

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

    # 2. Analysis: one model call, skipped when retrieval found nothing to compare.
    if evidence.clauses:
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
        },
        (
            AgentRole.VALIDATION,
            AgentRole.RECOMMENDATION,
            "findings.validated",
            f"Confirmed {confirmed} of {_plural(len(findings), 'finding')} against the cited text",
            {"support": {f.id: f.support.value for f in findings}, "notes": checked.notes},
        ),
    )

    # 5. Recommendation: one model call on validated gaps.
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
    status = derive_status(findings)
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
        summary=summarize(status, findings),
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
        ),
        review_state=ReviewState.UNREVIEWED,
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
