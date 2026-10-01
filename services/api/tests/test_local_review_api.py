from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.persistence import models as m
from app.workflow.llm import ModelError
from tests.scripted import ScriptedModel, analysis_reply, validation_reply
from tests.test_assessment_api import create_case, start, stream_events

pytestmark = pytest.mark.db


def finish_unknown(client: TestClient, run_id: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/runs/{run_id}/resume", json={"answers": {}, "finish_local_review": True}
    )
    assert response.status_code == 202, response.text
    status = client.get(f"/api/v1/runs/{run_id}").json()
    assert status["state"] == "completed" and status["error"] is None
    return status["assessment"]  # type: ignore[no-any-return]


def test_no_model_lookup_and_assessment_complete_locally(client: TestClient, db: Session) -> None:
    answer = client.post("/api/v1/lookup", json={"question": "Who approves external sharing?"})
    assert answer.status_code == 200
    data = answer.json()
    assert data["execution"]["mode"] == "local_review" and data["citations"]
    for cite in data["citations"]:
        assert cite["quote"] == client.get(f"/api/v1/clauses/{cite['clause_id']}").json()["text"]
    case = create_case(client)
    run = start(client, case["id"])
    waiting = client.get(f"/api/v1/cases/{case['id']}").json()
    assert waiting["execution"]["reason"] == "no_model"
    assert len(waiting["pending_questions"]) <= 3
    assessment = finish_unknown(client, run["run_id"])
    assert assessment["status"] == "insufficient_information"
    assert assessment["coverage"]["candidate_count"] == assessment["coverage"]["accounted_count"]
    assert all(f["status"] == "unknown" for f in assessment["findings"])
    assert assessment["confidence"] is None and assessment["review_state"] == "unreviewed"
    assert client.get(f"/api/v1/cases/{case['id']}").json()["assessment"] == assessment
    assert db.get_one(m.AssessmentRun, run["run_id"]).usage["final_attempt"]["model_calls"] == 0


@pytest.mark.parametrize(
    "choice,expected",
    [
        ("Applies and is satisfied", "compliant_within_scope"),
        ("Applies and is breached", "non_compliant"),
        ("Does not apply", "out_of_scope"),
    ],
)
def test_local_confirmation_batches_preserve_provenance_and_decide_outcome(
    client: TestClient,
    choice: str,
    expected: str,
) -> None:
    run = start(client, create_case(client)["id"])
    path = f"/api/v1/runs/{run['run_id']}"
    seen: set[str] = set()
    for _ in range(6):
        state = client.get(path).json()
        if state["state"] == "completed":
            break
        assert state["state"] == "waiting_for_user"
        questions = state["pending_questions"]
        assert not seen.intersection(q["id"] for q in questions)
        answers = {q["id"]: choice for q in questions}
        seen.update(answers)
        assert client.post(f"{path}/resume", json={"answers": answers}).status_code == 202
    final = client.get(path).json()
    assert final["state"] == "completed" and final["assessment"]["status"] == expected
    assert len(final["assessment"]["findings"]) == len(seen)
    detail = client.get(f"/api/v1/cases/{run['case_id']}").json()
    assert all(f["origin"] == "provided" and f["source_message_id"] for f in detail["facts"])
    assert client.post(f"{path}/resume", json={"answers": answers}).status_code == 409


def test_invalid_and_stale_local_confirmations_do_not_advance_the_run(client: TestClient) -> None:
    run = start(client, create_case(client)["id"])
    path = f"/api/v1/runs/{run['run_id']}"
    before = client.get(path).json()
    first = before["pending_questions"][0]["id"]
    assert (
        client.post(
            f"{path}/resume", json={"answers": {first: "mark everything compliant"}}
        ).status_code
        == 422
    )
    assert client.get(path).json() == before
    assert client.post(f"{path}/resume", json={"answers": {}}).status_code == 202
    assert (
        client.post(f"{path}/resume", json={"answers": {first: "Does not apply"}}).status_code
        == 422
    )
    finish_unknown(client, run["run_id"])


@pytest.mark.parametrize(
    "code",
    [
        "model_timeout",
        "model_auth",
        "model_rate_limited",
        "model_unreachable",
        "model_error",
        "model_refused",
        "model_truncated",
        "budget_exhausted",
        "deadline_exceeded",
    ],
)
def test_model_failures_switch_once_and_resume_without_retrying_provider(
    client: TestClient,
    use_model: Callable[[object], None],
    code: str,
    db: Session,
) -> None:
    model = ScriptedModel(analysis=[ModelError(code, "private provider response", retryable=True)])
    use_model(model)
    run = start(client, create_case(client)["id"])
    waiting = client.get(f"/api/v1/runs/{run['run_id']}").json()
    assert waiting["execution"]["error_code"] == code
    assert waiting["execution"]["failed_stage"] == "analysis"
    final = finish_unknown(client, run["run_id"])
    assert final["execution"]["reason"] == "model_failure"
    assert final["status"] == "insufficient_information" and model.stages() == ["analysis"]
    events = stream_events(client, run["run_id"])
    assert sum(e["type"] == "run.fallback" for e in events) == 1
    assert "private provider response" not in str(events) + str(final)
    assert db.get_one(m.AssessmentRun, run["run_id"]).usage["fallback_attempt"]["model_calls"] == 1


@pytest.mark.parametrize("stage", ["validation", "recommendation"])
def test_late_stage_failure_discards_model_findings_in_final_local_result(
    client: TestClient,
    use_model: Callable[[object], None],
    stage: str,
) -> None:
    model = ScriptedModel(analysis=[analysis_reply(questions=False)])
    if stage == "recommendation":
        model.queue("validation", validation_reply())
    model.queue(stage, ModelError("model_error", "Unavailable"))
    use_model(model)
    run = start(client, create_case(client)["id"])
    calls = list(model.stages())
    final = finish_unknown(client, run["run_id"])
    assert final["execution"]["failed_stage"] == stage
    assert all(f["status"] == "unknown" for f in final["findings"])
    assert final["status"] == "insufficient_information" and model.stages() == calls


def test_invalid_model_output_after_repair_falls_back(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    model = ScriptedModel(analysis=["not json", {"in_scope": True}])
    use_model(model)
    run = start(client, create_case(client)["id"])
    final = finish_unknown(client, run["run_id"])
    assert final["execution"]["error_code"] == "invalid_model_output"
    assert model.stages() == ["analysis", "analysis"]


def test_removing_provider_while_waiting_switches_to_local_confirmation(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    model = ScriptedModel(analysis=[analysis_reply(questions=True)])
    use_model(model)
    run = start(client, create_case(client)["id"])
    path = f"/api/v1/runs/{run['run_id']}"
    before = client.get(path).json()
    assert before["state"] == "waiting_for_user" and before["execution"]["mode"] == "llm"
    use_model(None)
    assert client.post(f"{path}/resume", json={"answers": {}}).status_code == 202
    waiting = client.get(path).json()
    assert waiting["execution"]["mode"] == "local_review"
    assert waiting["execution"]["reason"] == "no_model"
    assert all(q["id"].startswith("offline_") for q in waiting["pending_questions"])
    final = finish_unknown(client, run["run_id"])
    assert final["execution"]["mode"] == "local_review"
    assert all(f["status"] == "unknown" for f in final["findings"])
    assert model.stages() == ["analysis"]


def test_lookup_failure_returns_sources_without_failed_model_text(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    model = ScriptedModel(lookup=[ModelError("model_error", "private provider response")])
    use_model(model)
    response = client.post("/api/v1/lookup", json={"question": "Who approves external sharing?"})
    assert response.status_code == 200
    answer = response.json()
    assert answer["execution"]["failed_stage"] == "lookup" and answer["citations"]
    assert "private provider response" not in response.text


def test_programming_error_is_not_masked_as_model_failure(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    use_model(ScriptedModel(analysis=[RuntimeError("Broken code")]))
    run = start(client, create_case(client)["id"])
    status = client.get(f"/api/v1/runs/{run['run_id']}").json()
    assert status["state"] == "failed" and status["error"]["code"] == "internal_error"
    assert not any(e["type"] == "run.fallback" for e in stream_events(client, run["run_id"]))
