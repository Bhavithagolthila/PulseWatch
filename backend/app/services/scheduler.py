import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import delete, func, select

from ..config import settings
from ..database import SessionLocal
from ..models import HealthCheck, Monitor
from .checker import DOWN, CheckResult, run_check
from .health_checker import record_check

logger = logging.getLogger("pulsewatch.scheduler")
scheduler = BackgroundScheduler()


def _is_due(latest_check_at, interval_seconds: int, now: datetime) -> bool:
    if latest_check_at is None:
        return True
    if latest_check_at.tzinfo is None:  # defensive: treat naive values as UTC
        latest_check_at = latest_check_at.replace(tzinfo=timezone.utc)
    return (now - latest_check_at).total_seconds() >= interval_seconds


async def _check_all(monitors):
    # Run the due checks concurrently so one slow or down endpoint does not delay the rest.
    return await asyncio.gather(*(run_check(m.url) for m in monitors), return_exceptions=True)


def run_due_checks():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        monitors = db.scalars(select(Monitor).where(Monitor.enabled.is_(True))).all()
        latest = dict(
            db.execute(select(HealthCheck.monitored_api_id, func.max(HealthCheck.checked_at)).group_by(HealthCheck.monitored_api_id)).all()
        )
        due = [m for m in monitors if _is_due(latest.get(m.id), m.monitoring_interval, now)]
        if not due:
            return
        results = asyncio.run(_check_all(due))
        for monitor, result in zip(due, results):
            if isinstance(result, BaseException):
                result = CheckResult(DOWN, error_message=f"Unexpected error: {type(result).__name__}")
            try:
                record_check(db, monitor, result)
            except Exception:
                db.rollback()
                logger.exception("Could not save check result for monitor %s", monitor.id)
    except Exception:
        logger.exception("Scheduled check run failed")
    finally:
        db.close()


def prune_old_checks():
    """Delete health checks older than RETENTION_DAYS."""
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
        db.execute(delete(HealthCheck).where(HealthCheck.checked_at < cutoff))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Pruning old checks failed")
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(run_due_checks, "interval", seconds=15, id="monitor-poll", max_instances=1, coalesce=True)
        scheduler.add_job(prune_old_checks, "interval", hours=6, id="prune-checks", max_instances=1, coalesce=True)
        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
