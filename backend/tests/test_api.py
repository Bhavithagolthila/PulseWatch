from datetime import datetime
from unittest.mock import patch

from app.models import HealthCheck, Monitor
from app.services.checker import CheckResult


def create(client, name="Public API", url="https://example.com", **extra):
    with patch("app.api.monitors.validate_public_url"):
        return client.post("/api/monitors", json={"name": name, "url": url, **extra})


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_reject_local_url(client):
    response = client.post("/api/monitors", json={"name": "Local", "url": "http://127.0.0.1"})
    assert response.status_code == 422


def test_reject_blank_name(client):
    assert create(client, name="   ").status_code == 422


def test_name_is_trimmed(client):
    assert create(client, name="  Padded  ").json()["name"] == "Padded"


def test_crud(client):
    created = create(client)
    assert created.status_code == 201
    monitor_id = created.json()["id"]
    assert created.json()["last_check"] is None
    assert len(client.get("/api/monitors").json()) == 1
    assert client.get(f"/api/monitors/{monitor_id}").status_code == 200
    assert client.get("/api/monitors/999").status_code == 404

    with patch("app.api.monitors.validate_public_url"):
        updated = client.put(
            f"/api/monitors/{monitor_id}",
            json={"name": "Updated", "url": "https://example.org", "monitoring_interval": 600, "enabled": False},
        )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated" and updated.json()["enabled"] is False

    assert client.delete(f"/api/monitors/{monitor_id}").status_code == 204
    assert client.get(f"/api/monitors/{monitor_id}").status_code == 404


def test_interval_limits(client):
    assert create(client, monitoring_interval=5).status_code == 422
    assert create(client, monitoring_interval=100000).status_code == 422


def test_delete_removes_check_history(client, db):
    monitor_id = create(client).json()["id"]
    db.add(HealthCheck(monitored_api_id=monitor_id, status="HEALTHY"))
    db.commit()
    client.delete(f"/api/monitors/{monitor_id}")
    assert db.query(HealthCheck).count() == 0


def test_manual_check_persists_and_appears_everywhere(client):
    monitor_id = create(client).json()["id"]

    async def fake_run_check(url):
        return CheckResult("HEALTHY", 200, 34.5)

    with patch("app.services.health_checker.run_check", fake_run_check):
        result = client.post(f"/api/monitors/{monitor_id}/check")

    assert result.status_code == 200 and result.json()["response_time_ms"] == 34.5
    assert len(client.get(f"/api/monitors/{monitor_id}/history").json()) == 1
    assert client.get("/api/dashboard/stats").json()["healthy"] == 1
    listed = client.get("/api/monitors").json()[0]
    assert listed["latest_status"] == "HEALTHY"
    assert listed["last_check"]["response_time_ms"] == 34.5


def test_timestamps_are_timezone_aware(client):
    """Regression: SQLite used to return naive times, which browsers read as local time."""
    monitor_id = create(client).json()["id"]

    async def fake_run_check(url):
        return CheckResult("HEALTHY", 200, 10.0)

    with patch("app.services.health_checker.run_check", fake_run_check):
        client.post(f"/api/monitors/{monitor_id}/check")
    assert parse(client.get("/api/monitors").json()[0]["created_at"]).tzinfo is not None
    assert parse(client.get(f"/api/monitors/{monitor_id}/history").json()[0]["checked_at"]).tzinfo is not None


def test_history_pagination(client, db):
    monitor_id = create(client).json()["id"]
    db.add_all([HealthCheck(monitored_api_id=monitor_id, status="HEALTHY", http_status_code=200 + i) for i in range(5)])
    db.commit()
    page = client.get(f"/api/monitors/{monitor_id}/history?limit=2&offset=1").json()
    assert len(page) == 2
    assert client.get(f"/api/monitors/{monitor_id}/history?limit=0").status_code == 422


def test_incidents_only_bad_checks_with_monitor_name(client, db):
    monitor_id = create(client, name="Billing API").json()["id"]
    db.add_all(
        [
            HealthCheck(monitored_api_id=monitor_id, status="HEALTHY"),
            HealthCheck(monitored_api_id=monitor_id, status="DEGRADED", http_status_code=500),
            HealthCheck(monitored_api_id=monitor_id, status="DOWN", error_message="Request timed out."),
        ]
    )
    db.commit()
    incidents = client.get("/api/incidents").json()
    assert sorted(i["status"] for i in incidents) == ["DEGRADED", "DOWN"]
    assert {i["monitor_name"] for i in incidents} == {"Billing API"}


def test_changing_url_resets_stale_status(client, db):
    monitor_id = create(client).json()["id"]
    monitor = db.get(Monitor, monitor_id)
    monitor.latest_status = "DOWN"
    db.commit()
    with patch("app.api.monitors.validate_public_url"):
        out = client.put(f"/api/monitors/{monitor_id}", json={"name": "Same", "url": "https://other.example.org"}).json()
    assert out["latest_status"] is None
