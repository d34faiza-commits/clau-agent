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


def test_route_planned_intent_is_flagged():
    body = client.post("/route", json={"intent": "inquiry-reply"}).json()
    assert body["status"] == "planned"


def test_route_unknown_intent_404():
    response = client.post("/route", json={"intent": "make-coffee"})
    assert response.status_code == 404


def test_no_publish_endpoint():
    paths = {route.path for route in app.routes}
    assert not any("publish" in p or "send" in p for p in paths)
