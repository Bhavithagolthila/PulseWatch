from datetime import datetime, timedelta, timezone

from app.models import HealthCheck, Monitor
from app.services.analytics import bucket_response_times


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_bucket_response_times_averages_per_half_hour():
    rows = [(utc(2026, 1, 1, 10, 5), 100.0), (utc(2026, 1, 1, 10, 25), 200.0), (utc(2026, 1, 1, 10, 31), 50.0)]
    assert bucket_response_times(rows) == [
        {"time": "2026-01-01T10:00:00+00:00", "response_time_ms": 150.0, "checks": 2},
        {"time": "2026-01-01T10:30:00+00:00", "response_time_ms": 50.0, "checks": 1},
    ]


def test_bucket_treats_naive_datetimes_as_utc():
    result = bucket_response_times([(datetime(2026, 1, 1, 10, 5), 10.0)])
    assert result[0]["time"].endswith("+00:00")


def add_monitor_with_checks(db, checks):
    monitor = Monitor(name="m", url="https://example.com", monitoring_interval=60)
    db.add(monitor)
    db.commit()
    now = datetime.now(timezone.utc)
    for status, ms, age_hours in checks:
        db.add(HealthCheck(monitored_api_id=monitor.id, status=status, response_time_ms=ms, checked_at=now - timedelta(hours=age_hours)))
    monitor.latest_status = checks[0][0]
    db.commit()
    return monitor


def test_stats_math_excludes_down_and_old_checks(client, db):
    add_monitor_with_checks(
        db,
        [
            ("HEALTHY", 100.0, 1),
            ("HEALTHY", 300.0, 2),
            ("DEGRADED", 200.0, 3),
            ("DOWN", None, 4),  # no response: not in availability or latency
            ("HEALTHY", 999.0, 30),  # older than 24h: ignored
        ],
    )
    stats = client.get("/api/dashboard/stats").json()
    assert stats["checks_last_24h"] == 4
    assert stats["availability_percent"] == 66.67  # 2 healthy / (2 healthy + 1 degraded)
    assert stats["average_response_time_ms"] == 200.0  # (100 + 300 + 200) / 3
    assert stats["healthy"] == 1 and stats["total_monitors"] == 1


def test_stats_with_no_data_returns_null_not_zero(client):
    stats = client.get("/api/dashboard/stats").json()
    assert stats["availability_percent"] is None
    assert stats["average_response_time_ms"] is None
    assert stats["total_monitors"] == 0
