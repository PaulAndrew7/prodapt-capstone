import hashlib
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import policies as policies_api
from app.api.deps import Principal, get_principal
from app.domain.contracts import Role
from app.main import app
from app.persistence import models as m
from app.seed import DEMO_DIR, DEMO_ORG_ID, load_manifest

pytestmark = pytest.mark.db


def test_ready_reports_database_and_migrations(client: TestClient) -> None:
    body = client.get("/health/ready").json()
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["migrations"] == "ok"


def test_library_lists_versions_and_the_one_in_force(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policies_api, "_today", lambda: date(2026, 9, 26))
    items = {p["id"]: p for p in client.get("/api/v1/policies").json()["items"]}
    assert len(items) == 11
    assert items["ds"]["active_version_id"] == "ds_v1"
    assert items["ea"]["active_version_id"] == "ea_v2"
    assert {v["id"] for v in items["cm"]["versions"]} == {"cm_v1", "cm_v2"}  # admin sees drafts

    monkeypatch.setattr(policies_api, "_today", lambda: date(2026, 10, 2))
    items = {p["id"]: p for p in client.get("/api/v1/policies").json()["items"]}
    assert items["ds"]["active_version_id"] == "ds_v2"


def test_requesters_do_not_see_drafts(client: TestClient) -> None:
    app.dependency_overrides[get_principal] = lambda: Principal(
        "user_priya", DEMO_ORG_ID, Role.REQUESTER
    )
    items = {p["id"]: p for p in client.get("/api/v1/policies").json()["items"]}
    assert [v["id"] for v in items["cm"]["versions"]] == ["cm_v1"]
    assert client.get("/api/v1/policy-versions/cm_v2").status_code == 404


def test_version_detail_matches_web_contract(client: TestClient) -> None:
    body = client.get("/api/v1/policy-versions/ds_v1").json()
    assert body["policy_title"] == "Customer Data Sharing Policy"
    clause = next(c for c in body["clauses"] if c["id"] == "ds_v1_4_4.2")
    assert clause["section_path"] == ["4", "4.2"]
    assert clause["kind"] == "requirement"
    assert clause["text"].startswith("External sharing of customer data requires written approval")


def test_clause_spans_point_into_page_text(client: TestClient) -> None:
    clauses = client.get("/api/v1/policy-versions/vd_v1/clauses").json()
    target = next(c for c in clauses if c["clause_key"] == "3.1")
    span = target["spans"][0]
    page = client.get(f"/api/v1/policy-versions/vd_v1/pages/{span['page_index']}").json()
    raw = page["text"][span["char_start"] : span["char_end"]]
    assert " ".join(raw.split()) == target["text"]
    assert {
        "clause_id": target["id"],
        "char_start": span["char_start"],
        "char_end": span["char_end"],
    } in page["spans"]


def test_source_serves_the_original_bytes(client: TestClient) -> None:
    doc = next(d for d in load_manifest()["documents"] if d["version_id"] == "ds_v1")
    r = client.get("/api/v1/policy-versions/ds_v1/source")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert hashlib.sha256(r.content).hexdigest() == doc["pdf_sha256"]
    assert r.content == (DEMO_DIR / doc["pdf"]).read_bytes()

    r = client.get("/api/v1/policy-versions/ds_v1/source?page=2", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/api/v1/policy-versions/ds_v1/source#page=2"
    assert client.get("/api/v1/policy-versions/ds_v1/source?page=99").status_code == 422


def test_other_organizations_documents_are_invisible(client: TestClient, db: Session) -> None:
    db.add(m.Organization(id="org_other", slug="other", name="Other Org"))
    db.flush()
    db.add(
        m.Policy(
            id="op",
            organization_id="org_other",
            slug="op",
            title="Other",
            category="c",
            business_area="b",
            owner="o",
        )
    )
    db.flush()
    db.add(
        m.PolicyVersion(
            id="op_v1",
            policy_id="op",
            label="v1",
            effective_from=date(2026, 1, 1),
            status="draft",
            index_status="ready",
            original_sha256="0" * 64,
            storage_key="originals/x",
        )
    )
    db.flush()
    assert "op" not in {p["id"] for p in client.get("/api/v1/policies").json()["items"]}
    for path in (
        "/api/v1/policy-versions/op_v1",
        "/api/v1/policy-versions/op_v1/source",
        "/api/v1/policies/op/versions",
    ):
        assert client.get(path).status_code == 404, path


def test_search_finds_the_worked_scenario_clause(client: TestClient) -> None:
    body = client.post(
        "/api/v1/search",
        json={
            "question": "Can we send customer records to an analytics vendor without data owner approval?",
            "as_of": "2026-09-25",
        },
    ).json()
    assert body["policy_snapshot_id"] == "snapshot_demo_v1"
    assert body["channels"] == ["lexical"]  # embeddings are disabled in tests
    top = body["hits"][0]
    assert top["clause"]["id"] == "ds_v1_4_4.2"
    assert top["citation"]["source_url"] == "/api/v1/policy-versions/ds_v1/source?page=2"
    assert top["citation"]["quote"] == top["clause"]["text"]


def test_search_respects_effective_dates_and_scope(client: TestClient) -> None:
    q = {"question": "retention period for an external share", "as_of": "2026-10-15"}
    ids = [h["clause"]["id"] for h in client.post("/api/v1/search", json=q).json()["hits"]]
    assert "ds_v2_4_4.5" in ids
    assert not any(i.startswith("ds_v1") for i in ids)

    scoped = client.post("/api/v1/search", json={**q, "policy_ids": ["rd"]}).json()["hits"]
    assert scoped and all(h["clause"]["policy_id"] == "rd" for h in scoped)


def test_lookup_is_explicitly_not_implemented(client: TestClient) -> None:
    r = client.post("/api/v1/lookup", json={"question": "Who approves external sharing?"})
    assert r.status_code == 501
    assert r.json()["code"] == "not_implemented"
