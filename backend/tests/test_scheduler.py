from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.models import HealthCheck, Monitor
from app.services import scheduler
from app.services.checker import CheckResult


def make_monitor(db, name, **kwargs):
    monitor = Monitor(name=name, url=f"https://{name}.example.com", monitoring_interval=60, **kwargs)
    db.add(monitor)
    db.commit()
    return monitor


def test_only_due_enabled_monitors_are_checked(client, db):
    never_checked = make_monitor(db, "never")
    recent = make_monitor(db, "recent")
    paused = make_monitor(db, "paused", enabled=False)
    db.add(HealthCheck(monitored_api_id=recent.id, status="HEALTHY", checked_at=datetime.now(timezone.utc) - timedelta(seconds=10)))
    db.commit()
    checked_urls = []

    async def fake_run_check(url):
        checked_urls.append(url)
        return CheckResult("HEALTHY", 200, 12.0)

    with patch.object(scheduler, "run_check", fake_run_check):
        scheduler.run_due_checks()

    assert checked_urls == [never_checked.url]
    db.expire_all()
    assert db.get(Monitor, never_checked.id).latest_status == "HEALTHY"
    assert db.get(Monitor, paused.id).latest_status is None


def test_one_crashing_check_does_not_stop_the_others(client, db):
    bad = make_monitor(db, "bad")
    good = make_monitor(db, "good")

    async def fake_run_check(url):
        if "bad" in url:
            raise RuntimeError("boom")
        return CheckResult("HEALTHY", 200, 5.0)

    with patch.object(scheduler, "run_check", fake_run_check):
        scheduler.run_due_checks()

    db.expire_all()
    assert db.get(Monitor, good.id).latest_status == "HEALTHY"
    assert db.get(Monitor, bad.id).latest_status == "DOWN"


def test_prune_old_checks_keeps_recent_rows(client, db):
    monitor = make_monitor(db, "prune")
    now = datetime.now(timezone.utc)
    db.add_all(
        [
            HealthCheck(monitored_api_id=monitor.id, status="HEALTHY", checked_at=now - timedelta(days=400)),
            HealthCheck(monitored_api_id=monitor.id, status="HEALTHY", checked_at=now - timedelta(days=1)),
        ]
    )
    db.commit()
    scheduler.prune_old_checks()
    db.expire_all()
    assert db.query(HealthCheck).count() == 1
