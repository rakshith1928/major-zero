"""Trip Guardian MVP — deadline watch, one-tap rebook, demo delay staging.

Design notes:
- Arrival prediction reuses the deterministic tracking sim plus any staged
  demo delay override; the public API keeps reporting simulated=True.
- The safer-alternative rule mirrors the pre-payment detector
  (detector-clean, earlier arrival) so Guardian and booking agree.
- Rebooks are always explicit: the old booking is marked SUPERSEDED and the
  new one starts PENDING_PAYMENT (no silent changes, no prorating).
- Delay overrides live in memory (single-worker deployments); they exist to
  stage delay scenarios for demos and tests, never real GPS data.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import Booking, Bus, Notification, User
from app.services import notifications as notify_service
from app.services import tracking as tracking_service
from app.services.detectors import deadline_buffer

router = APIRouter(prefix="/api/guardian", tags=["guardian"])


class CheckRequest(BaseModel):
    booking_ref: str


class RebookRequest(BaseModel):
    booking_ref: str
    bus_id: int


class SimulateDelayRequest(BaseModel):
    bus_id: int
    minutes: int = 0


def _owned_booking(db: Session, user: User, booking_ref: str) -> Booking:
    booking = (
        db.query(Booking)
        .filter_by(booking_ref=booking_ref, user_id=user.id)
        .one_or_none()
    )
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "booking not found")
    return booking


def _scheduled_arrival(booking: Booking, bus: Bus) -> datetime:
    return datetime.combine(booking.travel_date, bus.arrival_time) + timedelta(
        days=bus.arrival_day_offset
    )


def _predicted_arrival(booking: Booking, bus: Bus) -> datetime:
    return _scheduled_arrival(booking, bus) + timedelta(
        minutes=tracking_service.delay_for(bus.id)
    )


def _safe_alternative(db: Session, booking: Booking, bus: Bus) -> Bus | None:
    candidates = (
        db.query(Bus)
        .filter(
            func.lower(Bus.origin) == bus.origin.lower(),
            func.lower(Bus.destination) == bus.destination.lower(),
        )
        .order_by(Bus.arrival_time)
        .all()
    )
    for candidate in candidates:
        if (
            candidate.id != bus.id
            and candidate.arrival_time < bus.arrival_time
            and deadline_buffer(booking.deadline_time, candidate, booking.travel_date) is None
        ):
            return candidate
    return None


@router.post("/check")
def check(req: CheckRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = _owned_booking(db, user, req.booking_ref)
    if booking.deadline_time is None:
        return {"booking_ref": booking.booking_ref, "status": "NO_DEADLINE"}
    bus = db.get(Bus, booking.bus_id)
    arrival = _predicted_arrival(booking, bus)
    # The deadline is anchored to the scheduled arrival day: a delay that
    # pushes arrival past it means AT_RISK, even across midnight.
    deadline = datetime.combine(_scheduled_arrival(booking, bus).date(), booking.deadline_time)
    eta = tracking_service.eta_to_stop(bus, booking.travel_date, bus.destination)
    if arrival <= deadline:
        return {
            "booking_ref": booking.booking_ref,
            "status": "OK",
            "predicted_arrival": arrival.isoformat(),
            "deadline": deadline.isoformat(),
            "eta_minutes": eta["eta_minutes"],
        }
    alternative = _safe_alternative(db, booking, bus)
    already = (
        db.query(Notification)
        .filter_by(user_id=user.id, type="GUARDIAN_ALERT")
        .filter(Notification.body.contains(booking.booking_ref))
        .first()
    )
    if not already:
        notify_service.notify(
            db,
            user.id,
            "GUARDIAN_ALERT",
            f"Trip at risk: {booking.booking_ref}",
            f"Booking {booking.booking_ref} is now predicted to arrive {arrival.strftime('%H:%M')}, "
            f"past your {booking.deadline_time.strftime('%H:%M')} deadline. Open your ticket to rebook.",
        )
    db.commit()
    return {
        "booking_ref": booking.booking_ref,
        "status": "AT_RISK",
        "predicted_arrival": arrival.isoformat(),
        "deadline": deadline.isoformat(),
        "eta_minutes": eta["eta_minutes"],
        "alternative_bus_id": alternative.id if alternative else None,
    }


@router.post("/rebook")
def rebook(req: RebookRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = _owned_booking(db, user, req.booking_ref)
    if booking.status == "SUPERSEDED":
        raise HTTPException(status.HTTP_409_CONFLICT, "booking already superseded")
    current = db.get(Bus, booking.bus_id)
    alternative = db.get(Bus, req.bus_id)
    if alternative is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bus not found")
    if (
        alternative.origin.lower() != current.origin.lower()
        or alternative.destination.lower() != current.destination.lower()
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "rebook stays on the same route")
    booking.status = "SUPERSEDED"
    new_booking = Booking(
        user_id=user.id,
        bus_id=alternative.id,
        travel_date=booking.travel_date,
        passenger_profile_id=booking.passenger_profile_id,
        passenger_snapshot_encrypted=booking.passenger_snapshot_encrypted,
        boarding_point=booking.boarding_point,
        fare=alternative.base_fare,
        deadline_time=booking.deadline_time,
    )
    db.add(new_booking)
    db.flush()
    db.commit()
    return {
        "booking_ref": new_booking.booking_ref,
        "status": new_booking.status,
        "supersedes": booking.booking_ref,
        "fare": new_booking.fare,
    }


@router.post("/simulate-delay")
def simulate_delay(req: SimulateDelayRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ = user
    bus = db.get(Bus, req.bus_id)
    if bus is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bus not found")
    if req.minutes > 0:
        tracking_service.set_delay(bus.id, req.minutes)
    else:
        tracking_service.clear_delay(bus.id)
    return {"bus_id": bus.id, "delay_minutes": tracking_service.delay_for(bus.id)}
