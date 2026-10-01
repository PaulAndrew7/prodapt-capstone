"""Admin source lifecycle, dated graph and model-independent adoption of new policies."""

import json
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.config import get_settings
from app.domain.contracts import Role, SearchRequest
from app.main import app
from app.persistence import models as m
from app.retrieval.search import search
from app.seed import DEMO_ORG_ID
from app.workflow.retrieval import retrieve
from tests.pdfs import blank_pdf, make_pdf

pytestmark = pytest.mark.db


def source(text: str = "Modelinventorium records are retained for seven years.") -> bytes:
    return make_pdf(
        [
            [
                "1 Purpose",
                "This policy governs modelinventorium operations.",
                "2 Controls",
                "2.1 Records",
                text,
                "2.2 Approval",
                "Modelinventorium deployments must be approved.",
            ]
        ]
    )


def upload(client: TestClient, **kwargs: Any) -> dict[str, Any]:
    data = {
        "title": "Modelinventorium Policy",
        "category": "AI",
        "business_area": "Technology",
        "owner": "AI owner",
        "label": "v1",
        "effective_from": "2026-09-30",
        **kwargs,
    }
    response = client.post(
        "/api/v1/admin/policies/upload",
        data={"metadata": json.dumps(data)},
        files={"file": ("policy.pdf", source(), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def review_body(review: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    v = review["version"]
    return {
        "label": v["label"],
        "effective_from": v["effective_from"],
        "effective_to": v["effective_to"],
        "expected_revision": review["revision"],
        "clauses": {
            c["id"]: {
                "kind": c["kind"],
                "candidate": c["kind"] in ("requirement", "exception")
                or c["section_path"][-1] == "2.1",
            }
            for c in v["clauses"]
        },
        "relations": [],
        "review_confirmed": True,
        "acknowledge_warnings": True,
        **kwargs,
    }


def save(client: TestClient, review: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/admin/policy-versions/{review['version']['id']}/review",
        json=review_body(review, **kwargs),
    )
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore[no-any-return]


def publish(client: TestClient, review: dict[str, Any]) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/admin/policy-versions/{review['version']['id']}/publish",
        json={"expected_revision": review["revision"]},
    )
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore[no-any-return]


def test_upload_review_publish_adopts_general_obligation_without_a_model(
    client: TestClient,
    db: Session,
) -> None:
    draft = upload(client)
    v = draft["version"]
    assert v["status"] == "draft" and v["index_status"] == "ready"
    assert client.get(f"/api/v1/policy-versions/{v['id']}/source").content == source()
    req = SearchRequest(question="modelinventorium records", policy_ids=[v["policy_id"]])
    assert not search(db, DEMO_ORG_ID, req, None).hits
    assert (
        client.post(
            f"/api/v1/admin/policy-versions/{v['id']}/publish", json={"expected_revision": 0}
        ).status_code
        == 422
    )
    reviewed = save(client, draft)
    result = publish(client, reviewed)
    assert publish(client, reviewed) == result
    hits = search(db, DEMO_ORG_ID, req, None)
    assert hits.policy_snapshot_id == result["snapshot_id"] and hits.hits
    bundle = retrieve(
        db,
        DEMO_ORG_ID,
        snapshot_id=result["snapshot_id"],
        as_of=date(2026, 9, 30),
        query=req.question,
        embedder=None,
        policy_ids=[v["policy_id"]],
    )
    assert any(c.section == "2.1" and c.reviewed_candidate for c in bundle.clauses)
    case = client.post(
        "/api/v1/cases",
        json={
            "text": "We plan modelinventorium deployments and retain modelinventorium records.",
            "business_area": "Technology",
            "as_of": "2026-09-30",
        },
    ).json()
    run = client.post(f"/api/v1/cases/{case['id']}/runs").json()
    response = client.post(
        f"/api/v1/runs/{run['run_id']}/resume", json={"answers": {}, "finish_local_review": True}
    )
    assert response.status_code == 202
    final = client.get(f"/api/v1/runs/{run['run_id']}").json()["assessment"]
    records = next(c for c in v["clauses"] if c["section_path"][-1] == "2.1")
    assert any(f["requirement_id"] == records["id"] for f in final["findings"])
    assert (
        final["execution"]["mode"] == "local_review"
        and final["status"] == "insufficient_information"
    )
    graph = client.get(
        "/api/v1/policy-graph", params={"case_id": case["id"], "policy_id": v["policy_id"]}
    ).json()
    assert graph["snapshot_id"] == result["snapshot_id"]
    assert any(n["kind"] == "finding" for n in graph["nodes"])
    assert all(
        e["source"] in {n["id"] for n in graph["nodes"]}
        and e["target"] in {n["id"] for n in graph["nodes"]}
        for e in graph["edges"]
    )
    assert (
        db.scalar(select(func.count(m.AuditEvent.id)).where(m.AuditEvent.target_id == v["id"])) == 3
    )


def test_new_versions_do_not_rewrite_old_snapshot_or_original_source(
    client: TestClient, db: Session
) -> None:
    first = save(client, upload(client))
    one = publish(client, first)
    before = db.get_one(m.PolicyVersion, first["version"]["id"])
    original = (before.original_sha256, before.effective_to, dict(before.provenance))
    second = save(
        client, upload(client, policy_id=before.policy_id, label="v2", effective_from="2026-10-01")
    )
    two = publish(client, second)
    req = SearchRequest(
        question="modelinventorium", policy_ids=[before.policy_id], as_of=date(2026, 10, 1)
    )
    assert {h.clause.policy_version_id for h in search(db, DEMO_ORG_ID, req, None).hits} == {
        second["version"]["id"]
    }
    assert {
        h.clause.policy_version_id
        for h in search(db, DEMO_ORG_ID, req, None, snapshot_id=one["snapshot_id"]).hits
    } == {before.id}
    req.as_of = date(2026, 9, 30)
    assert {h.clause.policy_version_id for h in search(db, DEMO_ORG_ID, req, None).hits} == {
        before.id
    }
    db.refresh(before)
    assert (before.original_sha256, before.effective_to, before.provenance) == original
    assert one["snapshot_id"] != two["snapshot_id"]


def test_expired_latest_version_does_not_reactivate_older_version(
    client: TestClient, db: Session
) -> None:
    first = save(client, upload(client))
    publish(client, first)
    second = save(
        client,
        upload(
            client,
            policy_id=first["version"]["policy_id"],
            label="v2",
            effective_from="2026-10-01",
            effective_to="2026-10-02",
        ),
    )
    publish(client, second)
    req = SearchRequest(
        question="modelinventorium",
        policy_ids=[first["version"]["policy_id"]],
        as_of=date(2026, 10, 3),
    )
    assert not search(db, DEMO_ORG_ID, req, None).hits


@pytest.mark.parametrize("bad", [b"not a PDF", blank_pdf()])
def test_invalid_upload_rolls_back_policy_and_version(
    client: TestClient, db: Session, bad: bytes
) -> None:
    before = db.scalar(select(func.count(m.Policy.id)))
    response = client.post(
        "/api/v1/admin/policies/upload",
        data={
            "metadata": json.dumps(
                {
                    "title": "Broken",
                    "category": "AI",
                    "business_area": "Tech",
                    "owner": "Owner",
                    "label": "v1",
                    "effective_from": "2026-09-30",
                }
            )
        },
        files={"file": ("bad.pdf", bad)},
    )
    assert response.status_code == 422
    assert db.scalar(select(func.count(m.Policy.id))) == before


def test_oversized_upload_and_invalid_metadata(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    metadata = {"policy_id": "ds", "label": "v3", "effective_from": "2026-10-01"}
    monkeypatch.setattr(get_settings(), "max_upload_bytes", 10)
    assert (
        client.post(
            "/api/v1/admin/policies/upload",
            data={"metadata": json.dumps(metadata)},
            files={"file": ("bad.pdf", source())},
        ).status_code
        == 413
    )
    metadata["effective_to"] = "2020-01-01"
    assert (
        client.post(
            "/api/v1/admin/policies/upload",
            data={"metadata": json.dumps(metadata)},
            files={"file": ("bad.pdf", source())},
        ).status_code
        == 422
    )


def test_stale_reviews_published_edits_and_ambiguous_date_are_rejected(client: TestClient) -> None:
    draft = upload(client)
    review = save(client, draft)
    path = f"/api/v1/admin/policy-versions/{draft['version']['id']}"
    assert client.post(f"{path}/review", json=review_body(draft)).status_code == 409
    assert client.post(f"{path}/publish", json={"expected_revision": 0}).status_code == 409
    publish(client, review)
    assert client.post(f"{path}/review", json=review_body(review)).status_code == 409
    other = save(client, upload(client, policy_id=draft["version"]["policy_id"], label="v2"))
    assert (
        client.post(
            f"/api/v1/admin/policy-versions/{other['version']['id']}/publish",
            json={"expected_revision": other["revision"]},
        ).json()["code"]
        == "ambiguous_effective_date"
    )


def test_partial_review_and_definition_candidate_cannot_publish(client: TestClient) -> None:
    draft = upload(client)
    path = f"/api/v1/admin/policy-versions/{draft['version']['id']}"
    body = review_body(draft)
    body["clauses"].pop(next(iter(body["clauses"])))
    assert client.post(f"{path}/review", json=body).status_code == 422
    body = review_body(draft)
    cid = next(iter(body["clauses"]))
    body["clauses"][cid] = {"kind": "definition", "candidate": True}
    assert client.post(f"{path}/review", json=body).status_code == 422
    saved = save(client, draft, review_confirmed=False)
    assert (
        client.post(f"{path}/publish", json={"expected_revision": saved["revision"]}).status_code
        == 422
    )


def test_requesters_cannot_manage_or_see_draft_only_policy(client: TestClient) -> None:
    draft = upload(client)
    app.dependency_overrides[get_principal] = lambda: Principal(
        "user_priya", DEMO_ORG_ID, Role.REQUESTER
    )
    assert draft["version"]["policy_id"] not in {
        p["id"] for p in client.get("/api/v1/policies").json()["items"]
    }
    path = f"/api/v1/admin/policy-versions/{draft['version']['id']}"
    assert client.get(f"{path}/review").status_code == 403
    assert client.post(f"{path}/review", json=review_body(draft)).status_code == 403
    assert client.post(f"{path}/publish", json={"expected_revision": 0}).status_code == 403
    assert client.get(f"/api/v1/policy-versions/{draft['version']['id']}/source").status_code == 404


def test_foreign_policy_draft_and_graph_are_inaccessible(client: TestClient, db: Session) -> None:
    draft = save(client, upload(client))
    result = publish(client, draft)
    db.add(m.Organization(id="org_other", slug="other", name="Other Org"))
    db.flush()
    app.dependency_overrides[get_principal] = lambda: Principal(
        "user_priya", "org_other", Role.ADMIN
    )
    assert (
        client.get(f"/api/v1/admin/policy-versions/{draft['version']['id']}/review").status_code
        == 404
    )
    assert (
        client.get(
            "/api/v1/policy-graph", params={"snapshot_id": result["snapshot_id"]}
        ).status_code
        == 404
    )


@pytest.mark.parametrize("approved", [False, True])
def test_cross_policy_links_are_dated_and_only_approved_links_expand_evidence(
    client: TestClient,
    db: Session,
    approved: bool,
) -> None:
    draft = upload(client)
    source_id = next(c["id"] for c in draft["version"]["clauses"] if c["section_path"][-1] == "2.1")
    review = save(
        client,
        draft,
        relations=[
            {
                "source_clause_id": source_id,
                "target_clause_id": "ds_v1_4_4.2",
                "relation": "references",
                "approved": approved,
                "rationale": "Data-owner approval is also referenced by this control.",
            }
        ],
    )
    published = publish(client, review)
    evidence = retrieve(
        db,
        DEMO_ORG_ID,
        snapshot_id=published["snapshot_id"],
        as_of=date(2026, 9, 30),
        query="modelinventorium",
        embedder=None,
    )
    assert ("ds_v1_4_4.2" in evidence.by_id()) == approved
    future = client.get(
        "/api/v1/policy-graph",
        params={"policy_id": draft["version"]["policy_id"], "as_of": "2026-10-01"},
    ).json()
    assert not any(n["id"] == "clause:ds_v1_4_4.2" for n in future["nodes"])


def test_graph_filters_date_drafts_and_old_snapshot(client: TestClient) -> None:
    before = client.get(
        "/api/v1/policy-graph", params={"policy_id": "ds", "as_of": "2026-09-30"}
    ).json()
    after = client.get(
        "/api/v1/policy-graph", params={"policy_id": "ds", "as_of": "2026-10-01"}
    ).json()
    assert any(n["id"] == "version:ds_v1" for n in before["nodes"])
    assert not any(n["id"] == "version:ds_v2" for n in before["nodes"])
    assert any(n["id"] == "version:ds_v2" for n in after["nodes"])
    assert not any(n["id"] == "version:ds_v1" for n in after["nodes"])
    assert not any("cm_v2" in n["id"] for n in after["nodes"])
