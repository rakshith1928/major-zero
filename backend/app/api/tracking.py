"""T10 — public tracking endpoints (no auth: passengers check the map freely)."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Booking, Bus
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
    if bus is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bus not found")
    try:
        return service.eta_to_stop(bus, travel, stop)
    except service.UnknownStop as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"message": f"{stop} is not on this bus's corridor", "stops": exc.stops},
        )


@router.get("/routes")
def routes(origin: str, destination: str, deadline: str | None = None, db: Session = Depends(get_db)):
    """Best-route advisor: today's remaining buses ranked for one corridor.

    Earliest arrival first (deadline-clearing preferred), fare breaks ties.
    Pure schedule + simulation math; public like the other tracking endpoints.
    """
    from datetime import time as time_cls

    deadline_time = None
    if deadline:
        try:
            hh, mm = deadline.split(":")
            deadline_time = time_cls(int(hh), int(mm or 0))
        except (ValueError, AttributeError):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "deadline must be HH:MM")
    today = date.today()
    buses = (
        db.query(Bus)
        .filter(
            func.lower(Bus.origin) == origin.lower(),
            func.lower(Bus.destination) == destination.lower(),
        )
        .order_by(Bus.arrival_time)
        .all()
    )
    rows = []
    for bus in buses:
        pos = service.position_for(bus, today)
        if pos["status"] == "COMPLETED":
            continue
        booked = (
            db.query(func.count(Booking.id))
            .filter(Booking.bus_id == bus.id, Booking.travel_date == today)
            .filter(Booking.status.in_(["PENDING_PAYMENT", "PAID"]))
            .scalar()
        ) or 0
        arrival = (
            bus.arrival_time.hour * 60 + bus.arrival_time.minute
            if bus.arrival_day_offset == 0
            else 24 * 60 + bus.arrival_time.hour * 60 + bus.arrival_time.minute
        )
        rows.append(
            {
                "bus_id": bus.id,
                "operator": bus.operator,
                "bus_type": bus.bus_type,
                "departure": bus.departure_time.strftime("%H:%M"),
                "arrival": bus.arrival_time.strftime("%H:%M"),
                "arrival_day_offset": bus.arrival_day_offset,
                "fare": bus.base_fare,
                "seats_left": max(0, bus.total_seats - booked),
                "status": pos["status"],
                "eta_minutes": pos["remaining_minutes"],
                "_sort_arrival": arrival,
            }
        )

    def clears(row) -> bool:
        if deadline_time is None:
            return True
        limit = deadline_time.hour * 60 + deadline_time.minute
        return row["_sort_arrival"] <= limit

    ranked = sorted(rows, key=lambda r: (not clears(r), r["_sort_arrival"], r["fare"]))
    for row in ranked:
        del row["_sort_arrival"]
    if not ranked:
        exists = (
            db.query(Bus.id)
            .filter(
                func.lower(Bus.origin) == origin.lower(),
                func.lower(Bus.destination) == destination.lower(),
            )
            .first()
            is not None
        )
        reason = (
            "No buses left on this corridor today."
            if exists
            else f"We don't run {origin}→{destination} yet — try a corridor from the map."
        )
        return {
            "origin": origin, "destination": destination, "date": today.isoformat(),
            "simulated": True, "buses": [], "recommended_bus_id": None,
            "reason": reason,
        }
    winner = ranked[0]
    winner_clears = deadline_time is None or winner["arrival"] <= deadline
    if deadline_time is None:
        reason = "Earliest arrival of the day"
    elif winner_clears:
        reason = f"Earliest arrival before your {deadline} deadline"
    else:
        reason = f"Earliest arrival (misses your {deadline} deadline)"
    return {
        "origin": origin, "destination": destination, "date": today.isoformat(),
        "simulated": True, "buses": ranked,
        "recommended_bus_id": winner["bus_id"], "reason": reason,
    }
