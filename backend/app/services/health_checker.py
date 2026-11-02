"""Glue between the HTTP checker and the database."""
import asyncio

from sqlalchemy.orm import Session

from ..models import HealthCheck, Monitor
from .alerts import notify_status_change
from .checker import CheckResult, run_check


def record_check(db: Session, monitor: Monitor, result: CheckResult) -> HealthCheck:
    """Save one result and update the monitor's latest status (synchronous DB work)."""
    record = HealthCheck(
        monitored_api_id=monitor.id,
        status=result.status,
        http_status_code=result.http_status_code,
        response_time_ms=result.response_time_ms,
        error_message=result.error_message,
    )
    previous_status = monitor.latest_status
    db.add(record)
    monitor.latest_status = result.status
    db.commit()
    db.refresh(record)
    notify_status_change(previous_status, monitor, result)  # emails only on a state change
    return record


async def perform_check(db: Session, monitor: Monitor) -> HealthCheck:
    """Check a monitor and persist the result without blocking the event loop."""
    result = await run_check(monitor.url)
    return await asyncio.to_thread(record_check, db, monitor, result)
