"""Scenario -> clarification -> assessment -> source, through the API and database, with a
scripted model standing in for the provider (plan §9 checks)."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.domain.contracts import EventType, Role, RunState
from app.main import app
from app.persistence import models as m
from app.workflow.llm import ModelError
from app.workflow.orchestrator import append_event
from tests.scripted import (
    DS_42,
    DS_42_QUOTE,
    RECOMMENDATION,
    SCENARIO,
    VD_31,
    ScriptedModel,
    analysis_reply,
    validation_reply,
)

pytestmark = pytest.mark.db


@pytest.mark.parametrize(
    "answers",
    [
        {"q1": "x" * 4001},
        {f"q{i}": None for i in range(4)},
        {"x" * 129: "answer"},
        {"": "answer"},
    ],
)
def test_oversized_answers_do_not_mutate_waiting_run(
    client: TestClient, use_model: Callable[[object], None], answers: dict[str, str | None]
) -> None:
    use_model(ScriptedModel(analysis=[analysis_reply()]))
    case = create_case(client)
    run = start(client, case["id"])
    path = f"/api/v1/cases/{case['id']}"
    before = client.get(path).json()
    response = client.post(f"/api/v1/runs/{run['run_id']}/resume", json={"answers": answers})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert client.get(path).json() == before


def test_other_organization_cannot_read_or_mutate_case_or_run(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    use_model(ScriptedModel(analysis=[analysis_reply()]))
    case = create_case(client)
    run = start(client, case["id"])
    case_path = f"/api/v1/cases/{case['id']}"
    run_path = f"/api/v1/runs/{run['run_id']}"
    original_case = client.get(case_path).json()
    original_run = client.get(run_path).json()
    app.dependency_overrides[get_principal] = lambda: Principal(
        "foreign_user", "foreign_org", Role.ADMIN
    )
    assert client.get("/api/v1/cases").json()["items"] == []
    for method, path, body in (
        ("GET", case_path, None),
        ("GET", run_path, None),
        ("GET", f"{run_path}/events", None),
        ("POST", f"{case_path}/messages", {"text": "Change another organization's facts"}),
        ("POST", f"{case_path}/runs", None),
        ("POST", f"{run_path}/resume", {"answers": {}}),
        ("POST", f"{run_path}/cancel", None),
    ):
        response = client.request(method, path, json=body)
        assert response.status_code == 404, (method, path, response.text)
        assert response.json()["code"] == "not_found"
    del app.dependency_overrides[get_principal]
    assert client.get(case_path).json() == original_case
    assert client.get(run_path).json() == original_run


def create_case(client: TestClient, text: str = SCENARIO) -> dict[str, Any]:
    r = client.post(
        "/api/v1/cases",
        json={"text": text, "business_area": "Marketing analytics", "as_of": "2026-09-26"},
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def start(client: TestClient, case_id: str, key: str = "key-1") -> dict[str, Any]:
    r = client.post(f"/api/v1/cases/{case_id}/runs", headers={"Idempotency-Key": key})
    assert r.status_code == 202, r.text
    return r.json()  # type: ignore[no-any-return]


def stream_events(client: TestClient, run_id: str, **params: int) -> list[dict[str, Any]]:
    with client.stream("GET", f"/api/v1/runs/{run_id}/events", params=params) as r:
        assert r.status_code == 200
        body = r.read().decode()
    return [
        json.loads(line[len("data: ") :]) for line in body.splitlines() if line.startswith("data: ")
    ]


def test_worked_scenario_asks_then_completes_with_cited_violation(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    model = ScriptedModel(analysis=[analysis_reply(), analysis_reply(questions=False)])
    model.queue("validation", validation_reply())
    model.queue("recommendation", RECOMMENDATION)
    use_model(model)

    case = create_case(client)
    assert case["run_state"] is None and case["messages"][0]["text"] == SCENARIO
    run = start(client, case["id"])

    waiting = client.get(f"/api/v1/cases/{case['id']}").json()
    assert waiting["run_state"] == "waiting_for_user"
    assert [q["fact_key"] for q in waiting["pending_questions"]] == ["vendor_review_status"]
    assert waiting["pending_questions"][0]["clause_ref"] == VD_31
    assert waiting["messages"][-1]["role"] == "assistant"
    facts = {f["key"]: f for f in waiting["facts"]}
    assert facts["data_owner_approval"]["origin"] == "provided"
    assert facts["vendor_review_status"] == {
        **facts["vendor_review_status"],
        "value": None,
        "origin": "unknown",
    }
    assert model.stages() == ["analysis"]  # paused before risk, validation, recommendation

    r = client.post(f"/api/v1/runs/{run['run_id']}/resume", json={"answers": {"q_1": None}})
    assert r.status_code == 202, r.text
    assert model.stages() == ["analysis", "analysis", "validation", "recommendation"]
    assert "Answers to clarifying questions" in model.calls[1][1]

    done = client.get(f"/api/v1/cases/{case['id']}").json()
    assert done["run_state"] == "completed" and done["latest_run_id"] == run["run_id"]
    a = done["assessment"]
    assert a["status"] == "non_compliant"
    coverage = a["coverage"]
    assert coverage["gate_version"] == "retrieved-candidates-v1"
    assert coverage["candidate_count"] == len(coverage["rows"])
    assert coverage["accounted_count"] >= 2
    assert all(row["policy_version_id"] != "ds_v2" for row in coverage["rows"])
    assert client.get(f"/api/v1/runs/{run['run_id']}").json()["assessment"]["coverage"] == coverage
    findings = {f["requirement_id"]: f for f in a["findings"]}
    assert findings[DS_42]["status"] == "violated" and findings[DS_42]["support"] == "validated"
    assert findings[VD_31]["status"] == "unknown"  # missing is not the same as absent
    # Every verdict carries an evidence score; the headline takes the deciding finding's.
    breach = findings[DS_42]["confidence"]
    assert breach["band"] == "high"
    assert breach["score"] == sum(x["points"] for x in breach["factors"])
    assert all(f["confidence"] is not None for f in a["findings"])
    assert a["confidence"]["score"] == breach["score"]
    assert a["confidence"]["basis"].startswith("Decided by finding")
    # "I don't know" is recorded as a confirmed unknown, attributed to the answer message.
    vendor = next(f for f in done["facts"] if f["key"] == "vendor_review_status")
    assert vendor["value"] is None and vendor["origin"] == "unknown" and vendor["confirmed"]
    assert vendor["source_message_id"] == done["messages"][-1]["id"]

    citations = {c["id"]: c for c in a["citations"]}
    ds_cite = citations[findings[DS_42]["citation_ids"][0]]
    assert ds_cite["quote"] == DS_42_QUOTE and ds_cite["clause_id"] == DS_42
    assert ds_cite["source_url"] == "/api/v1/policy-versions/ds_v1/source?page=2"
    risk = next(r for r in a["risks"] if findings[DS_42]["id"] in r["finding_ids"])
    assert risk["severity"] == "high" and risk["likelihood"] == "unknown"
    assert [r["finding_ids"] for r in a["recommendations"]] == [["finding_1"], ["finding_2"]]
    assert all(set(r["citation_ids"]) <= set(citations) for r in a["recommendations"])
    assert any("went unanswered" in note for note in a["limitations"])

    # The cited source resolves to the stored PDF page.
    src = client.get(ds_cite["source_url"], follow_redirects=False)
    assert src.status_code == 307 and src.headers["location"].endswith("#page=2")

    # One ordered, gap-free progress log covers both attempts.
    events = stream_events(client, run["run_id"])
    assert [e["type"] for e in events] == [
        "run.queued",
        "run.started",
        "retrieval.completed",
        "analysis.completed",
        "clarification.required",
        "run.resumed",
        "retrieval.completed",
        "analysis.completed",
        "risk.completed",
        "validation.completed",
        "recommendation.completed",
        "run.completed",
    ]
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    assert events[-1]["payload"] == {"status": "non_compliant"}
    # Reconnecting after the last event of a finished run gets 204: stop reconnecting.
    r = client.get(
        f"/api/v1/runs/{run['run_id']}/events",
        headers={"Last-Event-ID": str(events[-1]["sequence"])},
    )
    assert r.status_code == 204
    assert [e["type"] for e in stream_events(client, run["run_id"], after=10)] == [
        "recommendation.completed",
        "run.completed",
    ]

    roles = [(x["sender"], x["recipient"]) for x in done["agent_messages"]]
    assert roles[-5:] == [
        ("retrieval", "analysis"),
        ("analysis", "risk"),
        ("risk", "validation"),
        ("validation", "recommendation"),
        ("recommendation", "gate"),
    ]
    status = client.get(f"/api/v1/runs/{run['run_id']}").json()
    assert status["result_status"] == "non_compliant" and status["error"] is None
    listed = client.get("/api/v1/cases").json()["items"][0]
    assert listed["id"] == case["id"] and listed["status"] == "non_compliant"
    assert listed["unresolved_facts"] == 1


def test_unconfirmed_claims_never_produce_compliance(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    reply = analysis_reply(questions=False)
    for f in reply["findings"]:
        f["status"] = "met"
    use_model(
        ScriptedModel(
            analysis=[reply],
            validation=[validation_reply(finding_1="supported", finding_2="unsupported")],
            recommendation=[],
        )
    )
    case = create_case(client)
    start(client, case["id"])
    a = client.get(f"/api/v1/cases/{case['id']}").json()["assessment"]
    assert a["status"] == "insufficient_information"
    assert any("could not be confirmed" in note for note in a["limitations"])


def test_validation_can_downgrade_an_unstated_violation_to_unknown(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    downgrade = {
        "checks": [
            {
                "finding_id": "finding_1",
                "verdict": "supported",
                "suggested_status": None,
                "reason": "Stated.",
            },
            {
                "finding_id": "finding_2",
                "verdict": "contradicted",
                "suggested_status": "unknown",
                "reason": "The requester did not say the review failed.",
            },
        ]
    }
    use_model(
        ScriptedModel(
            analysis=[analysis_reply(questions=False, vendor_status="violated")],
            validation=[downgrade],
            recommendation=[RECOMMENDATION],
        )
    )
    case = create_case(client)
    start(client, case["id"])
    a = client.get(f"/api/v1/cases/{case['id']}").json()["assessment"]
    vendor = next(f for f in a["findings"] if f["requirement_id"] == VD_31)
    assert vendor["status"] == "unknown" and "did not say" in vendor["rationale"]
    assert all(VD_31 not in [a_f for a_f in r["finding_ids"]] for r in a["risks"])
    assert a["status"] == "non_compliant"  # still decided by the stated breach of §4.2


def test_suggesting_the_findings_own_status_counts_as_agreement(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    """Seen live: an unknown finding "contradicted" with suggested_status "unknown"."""
    checks = {
        "checks": [
            {"finding_id": "finding_1", "verdict": "supported", "suggested_status": None,
             "reason": "Stated."},
            {"finding_id": "finding_2", "verdict": "contradicted", "suggested_status": "unknown",
             "reason": "The vendor review status is unknown."},
        ]
    }  # fmt: skip
    use_model(
        ScriptedModel(
            analysis=[analysis_reply(questions=False)],
            validation=[checks],
            recommendation=[RECOMMENDATION],
        )
    )
    case = create_case(client)
    start(client, case["id"])
    a = client.get(f"/api/v1/cases/{case['id']}").json()["assessment"]
    vendor = next(f for f in a["findings"] if f["requirement_id"] == VD_31)
    assert vendor["status"] == "unknown" and vendor["support"] == "validated"
    assert "Validation:" not in vendor["rationale"]


def test_model_scope_claim_cannot_hide_unassessed_retrieved_candidates(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    model = ScriptedModel(
        analysis=[{"in_scope": False, "facts": [], "findings": [], "questions": []}]
    )
    use_model(model)
    case = create_case(client)
    start(client, case["id"])
    a = client.get(f"/api/v1/cases/{case['id']}").json()["assessment"]
    assert a["status"] == "insufficient_information" and "coverage gap" in a["summary"]
    assert a["coverage"]["unresolved_clause_ids"]
    assert "incomplete" in a["confidence"]["basis"]
    assert model.stages() == ["analysis"]


@pytest.mark.parametrize("as_of", ["2026-09-30", "2026-10-01"])
def test_coverage_uses_the_policy_version_in_force_and_preserves_omissions(
    client: TestClient, use_model: Callable[[object], None], as_of: str
) -> None:
    version = "ds_v1" if as_of == "2026-09-30" else "ds_v2"
    reply = analysis_reply(questions=False)
    reply["facts"] = [
        {**fact, "value": "Recorded before transfer"}
        if fact["key"] == "data_owner_approval"
        else dict(fact)
        for fact in reply["facts"]
    ]
    reply["findings"] = [reply["findings"][0]]
    reply["findings"][0].update(
        requirement_clause_id=f"{version}_4_4.2",
        status="met",
        evidence=[{"clause_id": f"{version}_4_4.2", "quote": DS_42_QUOTE}],
    )
    model = ScriptedModel(
        analysis=[reply],
        validation=[validation_reply(finding_1="supported")],
        recommendation=[{"actions": []}],
    )
    use_model(model)
    response = client.post(
        "/api/v1/cases",
        json={
            "text": "External sharing of customer data with a vendor has written data-owner approval "
            "recorded in the data-sharing register. The retention period was not discussed.",
            "business_area": "Marketing",
            "as_of": as_of,
        },
    )
    assert response.status_code == 201
    run = start(client, response.json()["id"])
    assessment = client.get(f"/api/v1/runs/{run['run_id']}").json()["assessment"]
    assert assessment["status"] == "insufficient_information"
    rows = assessment["coverage"]["rows"]
    assert {r["policy_version_id"] for r in rows if r["policy_version_id"].startswith("ds_")} == {
        version
    }
    if version == "ds_v2":
        omitted = next(r for r in rows if r["clause_id"] == "ds_v2_4_4.5")
        assert omitted["state"] == "unassessed" and omitted["finding_ids"] == []
        assert client.get(omitted["source_url"], follow_redirects=False).status_code == 307
    else:
        assert all(r["clause_id"] != "ds_v2_4_4.5" for r in rows)


def test_model_failure_in_required_mode_fails_without_a_result(
    client: TestClient, use_model: Callable[[object], None], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api import cases

    settings = cases.get_settings().model_copy(update={"llm_mode": "required"})
    monkeypatch.setattr(cases, "get_settings", lambda: settings)
    use_model(ScriptedModel(analysis=[ModelError("model_timeout", "Too slow.", retryable=True)]))
    case = create_case(client)
    run = start(client, case["id"])
    status = client.get(f"/api/v1/runs/{run['run_id']}").json()
    assert status["state"] == "failed" and status["assessment"] is None
    assert status["error"] == {"code": "model_timeout", "message": "Too slow.", "retryable": True}
    assert stream_events(client, run["run_id"])[-1]["type"] == "run.failed"


def test_one_repair_then_invalid_output_in_required_mode_fails(
    client: TestClient, use_model: Callable[[object], None], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api import cases

    settings = cases.get_settings().model_copy(update={"llm_mode": "required"})
    monkeypatch.setattr(cases, "get_settings", lambda: settings)
    model = ScriptedModel(analysis=["not json", {"in_scope": True}])
    use_model(model)
    case = create_case(client)
    run = start(client, case["id"])
    status = client.get(f"/api/v1/runs/{run['run_id']}").json()
    assert status["error"]["code"] == "invalid_model_output"
    assert model.stages() == ["analysis", "analysis"]
    assert "did not match the required JSON schema" in model.calls[1][1]


def test_duplicate_starts_and_resumes_do_not_launch_twice(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    model = ScriptedModel(
        analysis=[analysis_reply(), analysis_reply(questions=False)],
        validation=[validation_reply()],
        recommendation=[RECOMMENDATION],
    )
    use_model(model)
    case = create_case(client)
    first = start(client, case["id"], key="same")
    again = start(client, case["id"], key="same")
    assert again["run_id"] == first["run_id"] and model.stages() == ["analysis"]
    r = client.post(f"/api/v1/cases/{case['id']}/runs", headers={"Idempotency-Key": "other"})
    assert r.status_code == 409 and r.json()["code"] == "run_active"
    r = client.post(f"/api/v1/cases/{case['id']}/messages", json={"text": "More detail."})
    assert r.status_code == 409

    url = f"/api/v1/runs/{first['run_id']}/resume"
    assert client.post(url, json={"answers": {"q_9": "x"}}).status_code == 422
    assert client.post(url, json={"answers": {"q_1": "Yes, approved"}}).status_code == 202
    r = client.post(url, json={"answers": {"q_1": "Yes, approved"}})
    assert r.status_code == 409 and r.json()["code"] == "not_waiting"
    assert model.stages().count("analysis") == 2


def test_cancel_while_waiting_and_between_stages(
    client: TestClient,
    use_model: Callable[[object], None],
    session_factory: Callable[[], Session],
) -> None:
    use_model(ScriptedModel(analysis=[analysis_reply()]))
    case = create_case(client)
    run = start(client, case["id"])
    r = client.post(f"/api/v1/runs/{run['run_id']}/cancel")
    assert r.json()["state"] == "canceled"
    r = client.post(f"/api/v1/runs/{run['run_id']}/resume", json={"answers": {"q_1": None}})
    assert r.status_code == 409
    assert stream_events(client, run["run_id"])[-1]["type"] == "run.canceled"

    # A cancel that lands while the model is working: nothing after it is published.
    def cancel_then_answer(_: str) -> dict[str, Any]:
        with session_factory() as s:
            row = s.scalars(
                select(m.AssessmentRun).where(m.AssessmentRun.case_id == case2["id"])
            ).one()
            row.state = RunState.CANCELED
            append_event(s, row.id, EventType.RUN_CANCELED)
            s.commit()
        return analysis_reply(questions=False)

    model = ScriptedModel(analysis=[cancel_then_answer])
    use_model(model)
    case2 = create_case(client)
    run2 = start(client, case2["id"])
    status = client.get(f"/api/v1/runs/{run2['run_id']}").json()
    assert status["state"] == "canceled" and status["assessment"] is None
    types = [e["type"] for e in stream_events(client, run2["run_id"])]
    assert types[-1] == "run.canceled" and "analysis.completed" not in types
    assert model.stages() == ["analysis"]


def test_no_model_in_required_mode_is_a_clear_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api import cases, search

    settings = cases.get_settings().model_copy(update={"llm_mode": "required"})
    monkeypatch.setattr(cases, "get_settings", lambda: settings)
    monkeypatch.setattr(search, "get_settings", lambda: settings)
    case = create_case(client)
    r = client.post(f"/api/v1/cases/{case['id']}/runs")
    assert r.status_code == 503 and r.json()["code"] == "model_not_configured"
    r = client.post("/api/v1/lookup", json={"question": "Who approves external sharing?"})
    assert r.status_code == 503 and r.json()["code"] == "model_not_configured"


def test_follow_up_starts_a_new_revision_with_everything_said(
    client: TestClient, use_model: Callable[[object], None], db: Session
) -> None:
    model = ScriptedModel(
        analysis=[analysis_reply(questions=False), analysis_reply(questions=False)],
        validation=[validation_reply(), validation_reply()],
        recommendation=[RECOMMENDATION, RECOMMENDATION],
    )
    use_model(model)
    case = create_case(client)
    first = start(client, case["id"], key="a")
    r = client.post(
        f"/api/v1/cases/{case['id']}/messages",
        json={"text": "Update: the data owner has now approved it in writing."},
    )
    assert r.status_code == 201
    second = start(client, case["id"], key="b")
    assert second["run_id"] != first["run_id"]
    revisions = db.scalars(
        select(m.ScenarioRevision)
        .where(m.ScenarioRevision.case_id == case["id"])
        .order_by(m.ScenarioRevision.revision_number)
    ).all()
    assert [r.revision_number for r in revisions] == [1, 2]
    assert revisions[1].text.endswith("approved it in writing.")
    assert revisions[1].parent_revision_id == revisions[0].id
    assert "approved it in writing" in model.calls[3][1]


def test_lookup_answers_with_checked_citations(
    client: TestClient, use_model: Callable[[object], None]
) -> None:
    good = {
        "answerable": True,
        "answer": "The data owner must approve in writing.",
        "evidence": [{"clause_id": DS_42, "quote": DS_42_QUOTE}],
    }
    made_up = {
        "answerable": True,
        "answer": "Anyone can approve.",
        "evidence": [{"clause_id": "zz_v1_1_1.1", "quote": "anyone"}],
    }
    use_model(ScriptedModel(lookup=[good, made_up]))
    q = {"question": "Who must approve sharing customer data externally?", "as_of": "2026-09-26"}
    a = client.post("/api/v1/lookup", json=q).json()
    assert a["support"] == "validated" and a["citations"][0]["quote"] == DS_42_QUOTE
    assert a["confidence"]["band"] == "high"
    assert a["snapshot_id"] == "snapshot_demo_v1"
    b = client.post("/api/v1/lookup", json=q).json()
    assert b["support"] == "unsupported" and b["citations"] == []
    assert b["answer"].startswith("No answer is shown")
    assert b["confidence"]["score"] == 0 and b["confidence"]["basis"] == "Answer withheld"
