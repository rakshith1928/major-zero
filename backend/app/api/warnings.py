"""T06 — warning outcome recording (FIRED / ACCEPTED / OVERRIDDEN)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import Booking, User, WarningLog

router = APIRouter(prefix="/api/warnings", tags=["warnings"])

OUTCOMES = {"FIRED", "ACCEPTED", "OVERRIDDEN"}


class OutcomeRequest(BaseModel):
    booking_ref: str
    detector: str
    outcome: str


@router.post("/outcome")
def record_outcome(
    req: OutcomeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.outcome not in OUTCOMES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown outcome")
    booking = (
        db.query(Booking).filter_by(booking_ref=req.booking_ref, user_id=user.id).one_or_none()
    )
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown booking")
    db.add(
        WarningLog(
            user_id=user.id,
            booking_id=booking.id,
            detector=req.detector,
            outcome=req.outcome,
            detail="{}",
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/booking/{booking_ref}")
def for_booking(
    booking_ref: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking).filter_by(booking_ref=booking_ref, user_id=user.id).one_or_none()
    )
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown booking")
    rows = db.query(WarningLog).filter_by(booking_id=booking.id).all()
    return {
        "warnings": [
            {"detector": r.detector, "outcome": r.outcome} for r in rows
        ]
    }
