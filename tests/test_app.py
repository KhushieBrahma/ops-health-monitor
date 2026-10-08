import pytest

from app import app


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_create_and_list_task(client):
    resp = client.post("/api/tasks", json={"title": "deploy to EC2"})
    assert resp.status_code == 201
    task_id = resp.get_json()["id"]
    titles = [t["title"] for t in client.get("/api/tasks").get_json()]
    assert "deploy to EC2" in titles
    assert client.delete(f"/api/tasks/{task_id}").status_code == 204


def test_create_task_requires_title(client):
    resp = client.post("/api/tasks", json={"title": "   "})
    assert resp.status_code == 400


def test_delete_missing_task_returns_404(client):
    assert client.delete("/api/tasks/99999").status_code == 404


def test_metrics_exposes_prometheus_format(client):
    client.get("/health")
    body = client.get("/metrics").get_data(as_text=True)
    assert "app_requests_total" in body
    assert "app_uptime_seconds" in body
