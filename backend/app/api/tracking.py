"""T10 — public tracking endpoints (no auth: passengers check the map freely)."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Bus
from app.services import tracking as service

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


@router.get("/positions")
def positions(db: Session = Depends(get_db)):
    today = date.today()
    buses = db.query(Bus).all()
    return {
        "simulated": True,
        "as_of": today.isoformat(),
        "buses": [service.position_for(b, today) for b in buses],
    }


@router.get("/eta")
def eta(bus_id: int, travel_date: str, stop: str, db: Session = Depends(get_db)):
    from datetime import date as date_cls

    travel = date_cls.fromisoformat(travel_date)
    bus = db.get(Bus, bus_id)
    return service.eta_to_stop(bus, travel, stop)
