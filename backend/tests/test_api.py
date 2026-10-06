from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_agents_carry_forbidden_actions():
    agents = client.get("/agents").json()["agents"]
    assert agents
    for agent in agents:
        assert "publish" in agent["forbidden_actions"]
        assert "self_approve" in agent["forbidden_actions"]


def test_route_active_intent():
    body = client.post("/route", json={"intent": "caption"}).json()
    assert body["pillar"] == 1
    assert body["skill"] == "draft-caption"
    assert body["status"] == "active"


def test_route_active_intent_next_step():
    body = client.post("/route", json={"intent": "caption"}).json()
    assert body["next_step"] == "produce_draft"


def test_route_planned_intent_is_flagged():
    body = client.post("/route", json={"intent": "inquiry-reply"}).json()
    assert body["status"] == "planned"
    assert body["next_step"] == "escalate_to_owner"


def test_route_unknown_intent_404_contract_shape():
    response = client.post("/route", json={"intent": "make-coffee"})
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "unknown_intent", "message": "Intent 'make-coffee' tidak dikenal; tanya requester."}
    }


def test_route_invalid_body_uses_contract_shape():
    response = client.post("/route", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "intent" in response.json()["error"]["message"]


def test_no_publish_endpoint():
    paths = {route.path for route in app.routes}
    assert not any("publish" in p or "send" in p for p in paths)
