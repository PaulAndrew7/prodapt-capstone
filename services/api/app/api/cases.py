"""Cases, assessment runs and run progress (plan §5.4, §5.5; F07, F12, F16).

A run executes as an in-process background task after the response is sent. Progress is a
small saved event log: the stream replays events after the last sequence the client saw,
then polls for new ones until the run ends. "Resume" saves clarification answers and runs
the whole sequence again with them; it reuses the run ID so the client's subscription stays
valid.
"""

import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentPrincipal, DbSession, Principal
from app.api.errors import AppError, not_found
from app.config import get_settings
from app.domain.contracts import (
    AgentMessage,
    Assessment,
    CaseDetail,
    CaseSummary,
    ClarificationQuestion,
    EventType,
    Fact,
    Message,
    NewCaseRequest,
    NewMessageRequest,
    Page,
    ResumeRequest,
    ReviewState,
    RunError,
    RunEvent,
    RunState,
    RunStatus,
)
from app.persistence import models as m
from app.persistence.db import get_session_factory
from app.retrieval.embeddings import get_embedder
from app.retrieval.search import latest_snapshot_id
from app.workflow import records
from app.workflow.analysis import Answer
from app.workflow.llm import SETUP_HINT, ModelClient, get_model_client
from app.workflow.orchestrator import (
    ACTIVE,
    TERMINAL,
    SessionFactory,
    WorkflowDeps,
    append_event,
    execute_run,
    latest_event,
    lock_run,
    run_config,
)

router = APIRouter(prefix="/api/v1", tags=["cases"])

POLL_SECONDS = 0.5
KEEPALIVE_SECONDS = 15.0
STREAM_SECONDS = 15 * 60


@dataclass
class RunLauncher:
    deps: WorkflowDeps

    def launch(self, background: BackgroundTasks, run_id: str) -> None:
        background.add_task(execute_run, self.deps, run_id)


def get_launcher(
    factory: Annotated[SessionFactory, Depends(get_session_factory)],
    model: Annotated[ModelClient | None, Depends(get_model_client)],
) -> RunLauncher:
    s = get_settings()
    return RunLauncher(
        WorkflowDeps(
            factory,
            model,
            get_embedder(),
            s.run_max_model_calls,
            s.run_deadline_seconds,
            allow_fallback=s.llm_mode != "required",
            call_timeout_seconds=s.llm_call_timeout_seconds,
        )
    )


Launcher = Annotated[RunLauncher, Depends(get_launcher)]
Factory = Annotated[Callable[[], Session], Depends(get_session_factory)]


# --- Loading and conversion ---------------------------------------------------------------


def _case_for(session: Session, principal: Principal, case_id: str) -> m.Case:
    case = session.get(m.Case, case_id)
    if case is None or case.organization_id != principal.organization_id:
        raise not_found("Case")
    return case


def _run_for(
    session: Session, principal: Principal, run_id: str, *, lock: bool = False
) -> m.AssessmentRun:
    run = lock_run(session, run_id) if lock else session.get(m.AssessmentRun, run_id)
    if run is None or run.organization_id != principal.organization_id:
        raise not_found("Run")
    return run


def _pending_questions(session: Session, run: m.AssessmentRun) -> list[ClarificationQuestion]:
    if run.state != RunState.WAITING_FOR_USER:
        return []
    event = latest_event(session, run.id, EventType.CLARIFICATION_REQUIRED)
    questions = event.payload.get("questions", []) if event else []
    return [ClarificationQuestion.model_validate(q) for q in questions]


def _facts(session: Session, run: m.AssessmentRun | None) -> list[Fact]:
    if run is None:
        return []
    rows = session.scalars(
        select(m.Fact).where(m.Fact.scenario_revision_id == run.scenario_revision_id)
    )
    return [Fact.model_validate(f) for f in rows]


def _run_status(session: Session, run: m.AssessmentRun) -> RunStatus:
    return RunStatus(
        run_id=run.id,
        case_id=run.case_id,
        state=run.state,
        result_status=run.result_status,
        assessment=Assessment.model_validate(run.assessment) if run.assessment else None,
        pending_questions=_pending_questions(session, run),
        error=RunError.model_validate(run.error) if run.error else None,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        execution=run.config.get("execution"),
    )


def _summary(session: Session, case: m.Case, run: m.AssessmentRun | None) -> CaseSummary:
    owner = session.get_one(m.User, case.owner_id)
    facts = _facts(session, run)
    return CaseSummary(
        id=case.id,
        title=case.title,
        owner=owner.display_name,
        business_area=case.business_area,
        status=run.result_status if run else None,
        run_state=run.state if run else None,
        unresolved_facts=sum(1 for f in facts if f.value is None),
        review_state=run.review_state if run else ReviewState.UNREVIEWED,
        updated_at=case.updated_at,
    )


def _detail(session: Session, case: m.Case) -> CaseDetail:
    run = records.latest_run(session, case.id)
    messages = session.scalars(
        select(m.CaseMessage)
        .where(m.CaseMessage.case_id == case.id)
        .order_by(m.CaseMessage.created_at, m.CaseMessage.id)
    )
    agent_messages: list[m.AgentMessageRow] = (
        list(
            session.scalars(
                select(m.AgentMessageRow)
                .where(m.AgentMessageRow.run_id == run.id)
                .order_by(m.AgentMessageRow.created_at, m.AgentMessageRow.elapsed_ms)
            )
        )
        if run
        else []
    )
    return CaseDetail(
        **_summary(session, case, run).model_dump(),
        as_of=case.as_of,
        scope=case.scope,
        scenario_text=records.scenario_text(session, case.id),
        policy_snapshot_id=run.snapshot_id
        if run
        else latest_snapshot_id(session, case.organization_id) or "",
        messages=[Message.model_validate(x) for x in messages],
        facts=_facts(session, run),
        latest_run_id=run.id if run else None,
        assessment=Assessment.model_validate(run.assessment) if run and run.assessment else None,
        pending_questions=_pending_questions(session, run) if run else [],
        agent_messages=[
            AgentMessage.model_validate(
                {
                    "message_id": a.id,
                    "sender": a.sender,
                    "recipient": a.recipient,
                    "type": a.type,
                    "summary": a.summary,
                    "causal_parent_id": a.causal_parent_id,
                    "at_ms": a.elapsed_ms,
                }
            )
            for a in agent_messages
        ],
        execution=run.config.get("execution") if run else None,
    )


# --- Cases --------------------------------------------------------------------------------


@router.get("/cases", response_model=Page[CaseSummary])
def list_cases(session: DbSession, principal: CurrentPrincipal) -> Page[CaseSummary]:
    cases = session.scalars(
        select(m.Case)
        .where(m.Case.organization_id == principal.organization_id)
        .order_by(m.Case.updated_at.desc(), m.Case.id)
    )
    return Page[CaseSummary](
        items=[_summary(session, c, records.latest_run(session, c.id)) for c in cases]
    )


@router.post("/cases", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
def create_case(
    body: NewCaseRequest, session: DbSession, principal: CurrentPrincipal
) -> CaseDetail:
    case = records.create_case(
        session,
        organization_id=principal.organization_id,
        owner_id=principal.user_id,
        text=body.text,
        business_area=body.business_area,
        as_of=body.as_of,
    )
    session.commit()
    return _detail(session, case)


@router.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, session: DbSession, principal: CurrentPrincipal) -> CaseDetail:
    return _detail(session, _case_for(session, principal, case_id))


@router.post(
    "/cases/{case_id}/messages", response_model=Message, status_code=status.HTTP_201_CREATED
)
def add_message(
    case_id: str, body: NewMessageRequest, session: DbSession, principal: CurrentPrincipal
) -> Message:
    """A follow-up detail. It takes effect when the next run starts."""
    case = _case_for(session, principal, case_id)
    run = records.latest_run(session, case.id)
    if run is not None and run.state in ACTIVE:
        raise AppError(409, "run_active", "Wait for the current run to finish, or cancel it.")
    message = records.add_user_message(session, case, body.text)
    session.commit()
    return Message.model_validate(message)


# --- Runs ---------------------------------------------------------------------------------


@router.post("/cases/{case_id}/runs", response_model=RunStatus, status_code=202)
def start_run(
    case_id: str,
    session: DbSession,
    principal: CurrentPrincipal,
    launcher: Launcher,
    background: BackgroundTasks,
    idempotency_key: Annotated[str | None, Header(max_length=128)] = None,
) -> RunStatus:
    """Create a run and start it. Repeating the same Idempotency-Key returns the same run."""
    case = session.scalars(
        select(m.Case)
        .where(m.Case.id == case_id, m.Case.organization_id == principal.organization_id)
        .with_for_update()
    ).first()
    if case is None:
        raise not_found("Case")
    key = idempotency_key or uuid.uuid4().hex
    existing = session.scalars(
        select(m.AssessmentRun).where(
            m.AssessmentRun.case_id == case.id, m.AssessmentRun.idempotency_key == key
        )
    ).first()
    if existing is not None:
        return _run_status(session, existing)
    latest = records.latest_run(session, case.id)
    if latest is not None and latest.state in ACTIVE:
        raise AppError(409, "run_active", "This case already has a run in progress.")
    if launcher.deps.model is None and not launcher.deps.allow_fallback:
        raise AppError(
            503,
            "model_not_configured",
            f"No language model is configured, so assessments cannot run. {SETUP_HINT}",
        )
    snapshot_id = latest_snapshot_id(session, principal.organization_id)
    if snapshot_id is None:
        raise AppError(503, "demo_not_seeded", "No policy snapshot exists. Seed the corpus first.")

    s = get_settings()
    run = records.create_run(
        session,
        case,
        created_by=principal.user_id,
        snapshot_id=snapshot_id,
        idempotency_key=key,
        config=run_config(launcher.deps.model, launcher.deps.embedder),
        budget={
            "max_model_calls": s.run_max_model_calls,
            "deadline_seconds": s.run_deadline_seconds,
        },
    )
    session.commit()
    launcher.launch(background, run.id)
    return _run_status(session, run)


@router.get("/runs/{run_id}", response_model=RunStatus)
def get_run(run_id: str, session: DbSession, principal: CurrentPrincipal) -> RunStatus:
    return _run_status(session, _run_for(session, principal, run_id))


@router.post("/runs/{run_id}/resume", response_model=RunStatus, status_code=202)
def resume_run(
    run_id: str,
    body: ResumeRequest,
    session: DbSession,
    principal: CurrentPrincipal,
    launcher: Launcher,
    background: BackgroundTasks,
) -> RunStatus:
    """Save clarification answers and assess again with them. Only a waiting run resumes, so
    a repeated request cannot launch a second attempt."""
    run = _run_for(session, principal, run_id, lock=True)
    if run.state != RunState.WAITING_FOR_USER:
        raise AppError(409, "not_waiting", "This run is not waiting for answers.")
    questions = _pending_questions(session, run)
    unknown_ids = sorted(set(body.answers) - {q.id for q in questions})
    if unknown_ids:
        raise AppError(422, "unknown_question", f"Unknown question IDs: {', '.join(unknown_ids)}.")
    values = {q.id: (body.answers.get(q.id) or "").strip() or None for q in questions}
    local = run.config.get("execution", {}).get("mode") == "local_review"
    if body.finish_local_review and not local:
        raise AppError(
            422, "not_local_review", "Only a local review can finish with remaining checks unknown."
        )
    if local:
        if any(
            values[q.id] is not None and values[q.id] not in (q.choices or []) for q in questions
        ):
            raise AppError(
                422,
                "invalid_confirmation",
                "Choose a listed disposition or leave the check unknown.",
            )
        if body.finish_local_review:
            run.config = {**run.config, "local_review_complete": True}
    message = m.CaseMessage(
        id=m.new_id("msg"),
        case_id=run.case_id,
        role="user",
        text="\n".join(f"{q.question} {values[q.id] or 'I don’t know.'}" for q in questions),
        created_at=records.now(),
    )
    session.add(message)
    session.flush()
    answers = [Answer(q.id, q.fact_key, q.question, values[q.id], message.id) for q in questions]
    run.state = RunState.QUEUED
    append_event(
        session,
        run.id,
        EventType.RUN_RESUMED,
        {
            "answers": [asdict(a) for a in answers],
            "execution_mode": "local_review" if local else "llm",
        },
    )
    session.get_one(m.Case, run.case_id).updated_at = records.now()
    session.commit()
    launcher.launch(background, run.id)
    return _run_status(session, run)


@router.post("/runs/{run_id}/cancel", response_model=RunStatus)
def cancel_run(run_id: str, session: DbSession, principal: CurrentPrincipal) -> RunStatus:
    """Stop further stages. A stage already waiting on the model may still finish, but its
    result is never published. Canceling a finished run changes nothing."""
    run = _run_for(session, principal, run_id, lock=True)
    if run.state in ACTIVE:
        run.state = RunState.CANCELED
        run.finished_at = records.now()
        append_event(session, run.id, EventType.RUN_CANCELED)
        session.get_one(m.Case, run.case_id).updated_at = records.now()
        session.commit()
    return _run_status(session, run)


def _sse(row: m.RunEventRow) -> str:
    event = RunEvent(
        event_id=row.id,
        run_id=row.run_id,
        sequence=row.sequence,
        occurred_at=row.occurred_at,
        type=EventType(row.type),
        payload=row.payload,
    )
    return f"id: {row.sequence}\nevent: {row.type}\ndata: {event.model_dump_json()}\n\n"


@router.get(
    "/runs/{run_id}/events",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}, 204: {"description": "Run ended"}},
)
def run_events(
    run_id: str,
    session: DbSession,
    principal: CurrentPrincipal,
    factory: Factory,
    after: Annotated[int, Query(ge=0)] = 0,
    last_event_id: Annotated[str | None, Header()] = None,
) -> Response:
    """Server-sent events. Replays events after `after` (or the Last-Event-ID a reconnecting
    browser sends), then streams new ones until the run ends. A 204 tells the browser the run
    has ended and there is nothing more, so it stops reconnecting."""
    run = _run_for(session, principal, run_id)
    start = max(after, int(last_event_id) if last_event_id and last_event_id.isdigit() else 0)
    newer = session.scalar(
        select(func.count()).where(m.RunEventRow.run_id == run.id, m.RunEventRow.sequence > start)
    )
    if run.state in TERMINAL and not newer:
        return Response(status_code=204)

    def stream() -> Iterator[str]:
        last, quiet, ends = start, 0.0, time.monotonic() + STREAM_SECONDS
        yield "retry: 2000\n\n"
        while time.monotonic() < ends:
            with factory() as s:
                rows = s.scalars(
                    select(m.RunEventRow)
                    .where(m.RunEventRow.run_id == run_id, m.RunEventRow.sequence > last)
                    .order_by(m.RunEventRow.sequence)
                ).all()
                state = s.scalar(select(m.AssessmentRun.state).where(m.AssessmentRun.id == run_id))
            for row in rows:
                last = row.sequence
                yield _sse(row)
            if not rows and state in TERMINAL:
                return
            if rows:
                quiet = 0.0
                continue
            time.sleep(POLL_SECONDS)
            quiet += POLL_SECONDS
            if quiet >= KEEPALIVE_SECONDS:
                quiet = 0.0
                yield ": keep-alive\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
