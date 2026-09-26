from fastapi.testclient import TestClient


def test_live_needs_no_database(plain_client: TestClient) -> None:
    r = plain_client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "checks": {"process": "ok"}}


def test_unknown_route_uses_error_envelope(plain_client: TestClient) -> None:
    r = plain_client.get("/api/v1/definitely-not-a-route")
    body = r.json()
    assert r.status_code == 404
    assert body["code"] == "not_found"
    assert body["retryable"] is False
    assert body["request_id"] == r.headers["X-Request-ID"]


def test_request_id_is_echoed_when_safe(plain_client: TestClient) -> None:
    r = plain_client.get("/health/live", headers={"X-Request-ID": "abc-123"})
    assert r.headers["X-Request-ID"] == "abc-123"
    r = plain_client.get("/health/live", headers={"X-Request-ID": "<script>"})
    assert r.headers["X-Request-ID"] != "<script>"


def test_validation_errors_are_safe(client: TestClient) -> None:
    r = client.post("/api/v1/search", json={"question": ""})
    body = r.json()
    assert r.status_code == 422
    assert body["code"] == "validation_error"
    assert body["details"][0]["loc"] == ["body", "question"]


def test_openapi_lists_core_routes(plain_client: TestClient) -> None:
    paths = plain_client.get("/openapi.json").json()["paths"]
    for route in (
        "/api/v1/policies",
        "/api/v1/policy-versions/{version_id}",
        "/api/v1/policy-versions/{version_id}/source",
        "/api/v1/search",
        "/health/ready",
    ):
        assert route in paths
