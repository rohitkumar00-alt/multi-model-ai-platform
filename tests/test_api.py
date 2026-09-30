from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
GOOD = {"question": "What is Python?", "model_ids": ["mock-fast", "mock-thoughtful"]}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_list_models():
    ids = [m["id"] for m in client.get("/api/models").json()]
    assert "mock-fast" in ids and "mock-slow" in ids


def test_ask_success():
    r = client.post("/api/ask", json=GOOD)
    assert r.status_code == 200
    body = r.json()
    assert body["succeeded"] == 2 and body["failed"] == 0
    assert [x["model_id"] for x in body["results"]] == GOOD["model_ids"]
    assert body["coordinator"]["final_answer"]


def test_frontend_is_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "Multi-Model Answer Platform" in r.text


def test_timeout_is_reported_not_raised():
    r = client.post("/api/ask", json={**GOOD, "model_ids": ["mock-fast", "mock-slow"], "timeout_seconds": 1.5})
    body = r.json()
    statuses = {x["model_id"]: x["status"] for x in body["results"]}
    assert statuses == {"mock-fast": "ok", "mock-slow": "timeout"}


def test_validation_errors():
    assert client.post("/api/ask", json={**GOOD, "question": "   "}).status_code == 422
    assert client.post("/api/ask", json={**GOOD, "question": "x" * 4001}).status_code == 422
    assert client.post("/api/ask", json={**GOOD, "model_ids": ["mock-fast"]}).status_code == 422
    assert client.post("/api/ask", json={**GOOD, "model_ids": ["mock-fast", "mock-fast"]}).status_code == 422
    assert client.post("/api/ask", json={**GOOD, "model_ids": ["mock-fast", "nope"]}).status_code == 422
    assert client.post("/api/ask", json={**GOOD, "timeout_seconds": 0}).status_code == 422
