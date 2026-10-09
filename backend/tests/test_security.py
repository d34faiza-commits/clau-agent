"""Pengamanan API (docs/security.md §3): input dibatasi, body kecil, Host dikenal, header keamanan,
error tanpa detail internal, docs mati di produksi, tidak ada CORS dan tidak ada endpoint tulis/publish."""

import importlib

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "intent",
    [
        "caption' OR '1'='1",  # SQL injection
        "../../etc/passwd",  # path traversal
        "<script>alert(1)</script>",  # XSS dipantulkan di pesan error
        "http://169.254.169.254/latest/meta-data",  # SSRF
        "caption\nX-Injected: 1",  # header / log injection
        "CAPTION",
        "",
        "a" * 65,
    ],
)
def test_route_rejects_malicious_or_malformed_intent(intent):
    response = client.post("/route", json={"intent": intent})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert intent not in response.text or intent == ""


def test_route_rejects_extra_fields():
    response = client.post("/route", json={"intent": "caption", "status": "active", "approval_min": "L0"})
    assert response.status_code == 422


def test_route_rejects_non_string_intent():
    assert client.post("/route", json={"intent": {"$ne": None}}).status_code == 422
    assert client.post("/route", json={"intent": ["caption"]}).status_code == 422


def test_body_size_limit():
    big = '{"intent": "' + "a" * (main.MAX_BODY_BYTES + 1) + '"}'
    response = client.post("/route", content=big, headers={"content-type": "application/json"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_chunked_body_without_length_rejected():
    def chunks():
        yield b'{"intent": "caption"}'

    response = client.post("/route", content=chunks(), headers={"content-type": "application/json"})
    assert response.status_code == 411


def test_unknown_host_rejected():
    assert client.get("/health", headers={"host": "evil.example"}).status_code == 400


def test_security_headers_on_every_response():
    for response in (client.get("/health"), client.get("/does-not-exist"), client.post("/route", json={"intent": "x-y"})):
        for key, value in main.SECURITY_HEADERS.items():
            assert response.headers.get(key) == value, (response.request.url, key)


def test_no_cors():
    response = client.get("/agents", headers={"origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers
    preflight = client.options("/route", headers={"origin": "https://evil.example", "access-control-request-method": "POST"})
    assert "access-control-allow-origin" not in preflight.headers


def test_errors_use_contract_shape_without_internals():
    not_found = client.get("/admin")
    assert not_found.status_code == 404
    assert not_found.json() == {"error": {"code": "not_found", "message": "Endpoint tidak ada."}}
    method = client.delete("/agents")
    assert method.status_code == 405
    assert method.json()["error"]["code"] == "method_not_allowed"


def test_internal_error_hides_details(monkeypatch):
    def boom():
        raise RuntimeError("secret path /srv/clau/.env")

    monkeypatch.setattr(main, "load_registry", boom)
    response = TestClient(app, raise_server_exceptions=False).get("/agents")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret" not in response.text and "/srv" not in response.text


def test_only_read_endpoints_and_route():
    # Tidak ada endpoint tulis selain /route (read-only lookup) dan tidak ada publish (AI-CONSTITUTION §4).
    paths = {(m, r.path) for r in app.routes for m in getattr(r, "methods", set()) if m not in {"HEAD", "OPTIONS"}}
    allowed = {("GET", "/health"), ("GET", "/agents"), ("GET", "/pillars"), ("POST", "/route")}
    assert {p for p in paths if not p[1].startswith(("/docs", "/openapi"))} == allowed
    assert not any("publish" in p for _, p in paths)


def test_docs_disabled_in_production(monkeypatch):
    monkeypatch.setenv("CLAU_ENV", "production")
    monkeypatch.delenv("CLAU_ENABLE_DOCS", raising=False)
    prod = importlib.reload(main)
    try:
        c = TestClient(prod.app)
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404
        assert c.get("/health").status_code == 200
    finally:
        monkeypatch.delenv("CLAU_ENV")
        importlib.reload(main)
