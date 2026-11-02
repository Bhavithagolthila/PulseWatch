from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import HealthCheck, Monitor
from ..schemas import CheckOut, MonitorCreate, MonitorOut, MonitorUpdate
from ..services.health_checker import perform_check
from ..services.security import UnsafeTarget, validate_public_url

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


def latest_checks(db: Session, monitor_ids: list[int]) -> dict[int, HealthCheck]:
    """Newest check per monitor in one query (ids only grow, so max(id) is the newest row)."""
    if not monitor_ids:
        return {}
    newest_ids = (
        select(func.max(HealthCheck.id))
        .where(HealthCheck.monitored_api_id.in_(monitor_ids))
        .group_by(HealthCheck.monitored_api_id)
    )
    rows = db.scalars(select(HealthCheck).where(HealthCheck.id.in_(newest_ids))).all()
    return {row.monitored_api_id: row for row in rows}


def to_out(monitor: Monitor, last: HealthCheck | None) -> MonitorOut:
    out = MonitorOut.model_validate(monitor)
    out.last_check = CheckOut.model_validate(last) if last else None
    return out


def get_monitor(monitor_id: int, db: Session) -> Monitor:
    monitor = db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(404, "Monitor not found.")
    return monitor


def ensure_public(url: str) -> None:
    try:
        validate_public_url(url)
    except UnsafeTarget as exc:
        raise HTTPException(422, str(exc))


@router.post("", response_model=MonitorOut, status_code=201)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)):
    ensure_public(str(payload.url))
    monitor = Monitor(
        name=payload.name,
        url=str(payload.url),
        monitoring_interval=payload.monitoring_interval,
        enabled=payload.enabled,
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return to_out(monitor, None)


@router.get("", response_model=list[MonitorOut])
def list_monitors(db: Session = Depends(get_db)):
    monitors = db.scalars(select(Monitor).order_by(Monitor.created_at.desc())).all()
    latest = latest_checks(db, [m.id for m in monitors])
    return [to_out(m, latest.get(m.id)) for m in monitors]


@router.get("/{monitor_id}", response_model=MonitorOut)
def read_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = get_monitor(monitor_id, db)
    return to_out(monitor, latest_checks(db, [monitor.id]).get(monitor.id))


@router.put("/{monitor_id}", response_model=MonitorOut)
def update_monitor(monitor_id: int, payload: MonitorUpdate, db: Session = Depends(get_db)):
    monitor = get_monitor(monitor_id, db)
    new_url = str(payload.url)
    ensure_public(new_url)
    if new_url != monitor.url:
        monitor.latest_status = None  # old status described a different endpoint
    monitor.name = payload.name
    monitor.url = new_url
    monitor.monitoring_interval = payload.monitoring_interval
    monitor.enabled = payload.enabled
    db.commit()
    db.refresh(monitor)
    return to_out(monitor, latest_checks(db, [monitor.id]).get(monitor.id))


@router.delete("/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = get_monitor(monitor_id, db)
    db.delete(monitor)
    db.commit()


@router.post("/{monitor_id}/check", response_model=CheckOut)
async def check_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = get_monitor(monitor_id, db)
    return await perform_check(db, monitor)


@router.get("/{monitor_id}/history", response_model=list[CheckOut])
def monitor_history(
    monitor_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    get_monitor(monitor_id, db)
    return db.scalars(
        select(HealthCheck)
        .where(HealthCheck.monitored_api_id == monitor_id)
        .order_by(HealthCheck.checked_at.desc(), HealthCheck.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
