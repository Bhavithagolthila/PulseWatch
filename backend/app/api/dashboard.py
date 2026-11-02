from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.analytics import dashboard_stats, response_times

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    return dashboard_stats(db)


@router.get("/response-times")
def times(db: Session = Depends(get_db)):
    return response_times(db)
