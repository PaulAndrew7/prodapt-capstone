"""Creating cases and runs. Shared by the API and the evaluation script so both go through
the same records and the same workflow."""

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.contracts import EventType, RunState
from app.persistence import models as m
from app.workflow.orchestrator import append_event


def now() -> datetime:
    # Explicit timestamps keep rows written in one transaction in order (see orchestrator).
    return datetime.now(UTC)


def title_for(text: str) -> str:
    first = text.strip().split("\n")[0]
    for stop in (". ", "? ", "! "):
        if stop in first:
            first = first.split(stop)[0]
    first = first.rstrip(".?! ")
    return first if len(first) <= 80 else first[:77].rsplit(" ", 1)[0] + "..."


def create_case(
    session: Session,
    *,
    organization_id: str,
    owner_id: str,
    text: str,
    business_area: str,
    as_of: date,
) -> m.Case:
    case = m.Case(
        id=m.new_id("case"),
        organization_id=organization_id,
        owner_id=owner_id,
        title=title_for(text),
        business_area=business_area.strip(),
        scope="Kestrel Mutual demo corpus",
        as_of=as_of,
        created_at=now(),
        updated_at=now(),
    )
    session.add(case)
    session.flush()
    add_user_message(session, case, text)
    return case


def add_user_message(session: Session, case: m.Case, text: str) -> m.CaseMessage:
    message = m.CaseMessage(
        id=m.new_id("msg"), case_id=case.id, role="user", text=text.strip(), created_at=now()
    )
    session.add(message)
    case.updated_at = now()
    session.flush()
    return message


def scenario_text(session: Session, case_id: str) -> str:
    """Everything the requester has said in this case, in order."""
    texts = session.scalars(
        select(m.CaseMessage.text)
        .where(m.CaseMessage.case_id == case_id, m.CaseMessage.role == "user")
        .order_by(m.CaseMessage.created_at, m.CaseMessage.id)
    ).all()
    return "\n\n".join(texts)


def latest_run(session: Session, case_id: str) -> m.AssessmentRun | None:
    return session.scalars(
        select(m.AssessmentRun)
        .where(m.AssessmentRun.case_id == case_id)
        .order_by(m.AssessmentRun.created_at.desc(), m.AssessmentRun.id)
        .limit(1)
    ).first()


def create_run(
    session: Session,
    case: m.Case,
    *,
    created_by: str,
    snapshot_id: str,
    idempotency_key: str,
    config: dict[str, Any],
    budget: dict[str, Any],
) -> m.AssessmentRun:
    """A new scenario revision holding everything said so far, and a queued run for it."""
    previous = latest_run(session, case.id)
    number = (
        session.scalar(
            select(func.max(m.ScenarioRevision.revision_number)).where(
                m.ScenarioRevision.case_id == case.id
            )
        )
        or 0
    ) + 1
    revision = m.ScenarioRevision(
        id=m.new_id("rev"),
        case_id=case.id,
        parent_revision_id=previous.scenario_revision_id if previous else None,
        revision_number=number,
        text=scenario_text(session, case.id),
        created_by=created_by,
    )
    session.add(revision)
    session.flush()
    run = m.AssessmentRun(
        id=m.new_id("run"),
        organization_id=case.organization_id,
        case_id=case.id,
        scenario_revision_id=revision.id,
        snapshot_id=snapshot_id,
        state=RunState.QUEUED,
        idempotency_key=idempotency_key,
        config=config,
        budget=budget,
        created_by=created_by,
        created_at=now(),
    )
    session.add(run)
    session.flush()
    append_event(session, run.id, EventType.RUN_QUEUED)
    case.updated_at = now()
    return run
