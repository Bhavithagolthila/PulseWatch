from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models import HealthCheck, Monitor

BUCKET_MINUTES = 30


def dashboard_stats(db: Session):
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    # Monitor counts per latest status, computed by the database.
    by_status = dict(db.execute(select(Monitor.latest_status, func.count()).group_by(Monitor.latest_status)).all())

    # One aggregate query instead of loading every check into Python.
    total, avg_ms, healthy, applicable = db.execute(
        select(
            func.count(HealthCheck.id),
            func.avg(HealthCheck.response_time_ms),  # DOWN checks store NULL, so they are ignored
            func.sum(case((HealthCheck.status == "HEALTHY", 1), else_=0)),
            func.sum(case((HealthCheck.status.in_(["HEALTHY", "DEGRADED"]), 1), else_=0)),
        ).where(HealthCheck.checked_at >= since)
    ).one()
    healthy, applicable = int(healthy or 0), int(applicable or 0)

    return {
        "total_monitors": sum(by_status.values()),
        "healthy": by_status.get("HEALTHY", 0),
        "degraded": by_status.get("DEGRADED", 0),
        "down": by_status.get("DOWN", 0),
        "pending": by_status.get(None, 0),
        "average_response_time_ms": round(float(avg_ms), 2) if avg_ms is not None else None,
        "availability_percent": round(healthy / applicable * 100, 2) if applicable else None,
        "checks_last_24h": int(total or 0),
        "availability_window": "Last 24 hours; HEALTHY / (HEALTHY + DEGRADED). DOWN checks are excluded because no valid HTTP response was received.",
    }


def bucket_response_times(rows, bucket_minutes: int = BUCKET_MINUTES):
    """Average (checked_at, response_ms) pairs into fixed time buckets, oldest first."""
    buckets: dict[datetime, list[float]] = {}
    for checked_at, ms in rows:
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=timezone.utc)
        start = checked_at.replace(minute=(checked_at.minute // bucket_minutes) * bucket_minutes, second=0, microsecond=0)
        buckets.setdefault(start, []).append(ms)
    return [
        {"time": start.isoformat(), "response_time_ms": round(sum(v) / len(v), 2), "checks": len(v)}
        for start, v in sorted(buckets.items())
    ]


def response_times(db: Session):
    """Average latency per 30 minutes (max 48 points) so the chart stays fast and readable."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = db.execute(
        select(HealthCheck.checked_at, HealthCheck.response_time_ms).where(
            HealthCheck.checked_at >= since, HealthCheck.response_time_ms.is_not(None)
        )
    ).all()
    return bucket_response_times([(r.checked_at, r.response_time_ms) for r in rows])
