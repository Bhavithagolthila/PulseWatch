from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import HealthCheck, Monitor
from ..schemas import CheckOut, IncidentOut

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentOut])
def incidents(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.execute(
        select(HealthCheck, Monitor.name)
        .join(Monitor, Monitor.id == HealthCheck.monitored_api_id)
        .where(HealthCheck.status.in_(["DEGRADED", "DOWN"]))
        .order_by(HealthCheck.checked_at.desc(), HealthCheck.id.desc())
        .limit(limit)
    ).all()
    return [IncidentOut(**CheckOut.model_validate(check).model_dump(), monitor_name=name) for check, name in rows]
