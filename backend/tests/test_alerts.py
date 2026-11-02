from unittest.mock import patch

import pytest

from app.models import Monitor
from app.services import alerts
from app.services.checker import CheckResult
from app.services.health_checker import record_check


@pytest.mark.parametrize(
    "previous,current,expected",
    [
        (None, "HEALTHY", None),
        (None, "DOWN", "down"),
        ("HEALTHY", "DOWN", "down"),
        ("HEALTHY", "DEGRADED", "degraded"),
        ("DEGRADED", "DOWN", "down"),
        ("DOWN", "DEGRADED", "degraded"),
        ("DOWN", "HEALTHY", "recovered"),
        ("DEGRADED", "HEALTHY", "recovered"),
        ("DOWN", "DOWN", None),
        ("HEALTHY", "HEALTHY", None),
    ],
)
def test_detect_event(previous, current, expected):
    assert alerts.detect_event(previous, current) == expected


def configure(monkeypatch):
    monkeypatch.setattr(alerts.settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(alerts.settings, "alert_email_to", "me@example.com")
    monkeypatch.setattr(alerts.settings, "alert_email_from", "pulsewatch@example.com")


def make(db):
    monitor = Monitor(name="Billing", url="https://billing.example.com")
    db.add(monitor)
    db.commit()
    return monitor


def test_state_change_sends_one_email_and_repeats_do_not(client, db, monkeypatch):
    configure(monkeypatch)
    sent = []
    monkeypatch.setattr(alerts, "send_email", lambda subject, body: sent.append((subject, body)))
    # Run the "background thread" inline so the test is deterministic.
    monkeypatch.setattr(alerts.threading, "Thread", lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})())
    monitor = make(db)

    record_check(db, monitor, CheckResult("HEALTHY", 200, 10.0))  # first healthy: silent
    record_check(db, monitor, CheckResult("DOWN", error_message="Request timed out."))  # alert
    record_check(db, monitor, CheckResult("DOWN", error_message="Request timed out."))  # still down: silent
    record_check(db, monitor, CheckResult("HEALTHY", 200, 12.0))  # recovered

    assert [s for s, _ in sent] == ["[PulseWatch] DOWN: Billing", "[PulseWatch] Recovered: Billing"]
    assert "Request timed out." in sent[0][1] and "https://billing.example.com" in sent[0][1]


def test_no_email_attempted_when_not_configured(client, db):
    monitor = make(db)
    with patch.object(alerts, "send_email") as send:
        record_check(db, monitor, CheckResult("DOWN", error_message="x"))
    send.assert_not_called()


def test_smtp_failure_never_breaks_a_check(client, db, monkeypatch):
    configure(monkeypatch)

    def boom(subject, body):
        raise OSError("smtp unreachable")

    monkeypatch.setattr(alerts, "send_email", boom)
    monkeypatch.setattr(alerts.threading, "Thread", lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})())
    monitor = make(db)
    record = record_check(db, monitor, CheckResult("DOWN", error_message="x"))
    assert record.status == "DOWN" and monitor.latest_status == "DOWN"


def test_alert_config_endpoint_hides_secrets(client, monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr(alerts.settings, "smtp_password", "super-secret")
    body = client.get("/api/alerts/config").json()
    assert body == {"configured": True, "recipient": "me@example.com"}


def test_test_email_not_configured_gives_clear_error(client):
    response = client.post("/api/alerts/test")
    assert response.status_code == 503 and "SMTP_HOST" in response.json()["detail"]


def test_test_email_success_and_failure(client, monkeypatch):
    configure(monkeypatch)
    with patch("app.api.alerts.send_email") as send:
        ok = client.post("/api/alerts/test")
    assert ok.status_code == 200 and ok.json() == {"sent_to": "me@example.com"}
    send.assert_called_once()

    with patch("app.api.alerts.send_email", side_effect=OSError("connection refused")):
        bad = client.post("/api/alerts/test")
    assert bad.status_code == 502 and "connection refused" in bad.json()["detail"]
