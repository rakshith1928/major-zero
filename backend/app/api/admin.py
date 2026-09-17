"""T11 — admin dashboard API (admin-only aggregates)."""

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import Booking, Bus, ChatMessage, Notification, Payment, User, WarningLog

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_admin(user)
    revenue = (
        db.query(func.coalesce(func.sum(Booking.fare), 0))
        .filter(Booking.status == "PAID", Booking.is_synthetic.is_(False))
        .scalar()
    )
    warnings = db.query(WarningLog.detector, WarningLog.outcome).all()
    by_detector: dict[str, dict] = {}
    for detector, outcome in warnings:
        entry = by_detector.setdefault(detector, {"fired": 0, "accepted": 0, "overridden": 0})
        if outcome == "FIRED":
            entry["fired"] += 1
        elif outcome == "ACCEPTED":
            entry["accepted"] += 1
        elif outcome == "OVERRIDDEN":
            entry["overridden"] += 1
    occupancy = (
        db.query(Bus.origin, Bus.destination, func.count(Booking.id))
        .outerjoin(
            Booking,
            (Booking.bus_id == Bus.id)
            & (Booking.status.in_(["PENDING_PAYMENT", "PAID"])),
        )
        .group_by(Bus.origin, Bus.destination)
        .all()
    )
    return {
        "totals": {
            "users": db.query(func.count(User.id)).scalar(),
            "bookings": db.query(func.count(Booking.id)).filter(Booking.is_synthetic.is_(False)).scalar(),
            "revenue": revenue,
            "chat_messages": db.query(func.count(ChatMessage.id)).scalar(),
            "payments": db.query(func.count(Payment.id)).scalar(),
            "notifications": db.query(func.count(Notification.id)).scalar(),
        },
        "warnings": by_detector,
        "demand": [
            {"origin": o, "destination": d, "active_bookings": n}
            for o, d, n in occupancy
        ],
    }
