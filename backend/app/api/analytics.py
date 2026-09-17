"""T09 — analytics endpoints (demand curve + peak flags)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import analytics as service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/demand")
def demand(origin: str, destination: str, date: str, db: Session = Depends(get_db)):
    from datetime import date as date_cls

    travel = date_cls.fromisoformat(date)
    return {
        "route": [origin, destination],
        "date": travel.isoformat(),
        "curve": service.demand_curve(db, origin, destination, travel),
    }
