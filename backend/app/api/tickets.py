"""T07 — ticket issue + conductor verification endpoints."""

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import Booking, Ticket, User
from app.services import tickets as ticket_service
from app.services import vault

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class VerifyRequest(BaseModel):
    code: str


class PayloadLookupRequest(BaseModel):
    qr_payload: str


@router.get("/{booking_ref}")
def get_ticket(booking_ref: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = (
        db.query(Booking).filter_by(booking_ref=booking_ref, user_id=user.id).one_or_none()
    )
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown booking")
    if booking.status != "PAID":
        raise HTTPException(status.HTTP_409_CONFLICT, "booking is not paid yet")
    ticket = db.query(Ticket).filter_by(booking_id=booking.id).one_or_none()
    if ticket is None:
        details = vault.decrypt_for_user(user.id, booking.passenger_snapshot_encrypted, db, booking.passenger_profile_id, "GET /api/tickets")
        payload = {
            "booking_ref": booking.booking_ref,
            "bus_id": booking.bus_id,
            "travel_date": booking.travel_date.isoformat(),
            "passenger": details,
        }
        qr_payload = ticket_service.sign_payload(payload)
        ticket = Ticket(booking_id=booking.id, qr_payload=qr_payload)
        db.add(ticket)
        try:
            db.commit()
        except IntegrityError:  # concurrent GET issued it first; reuse theirs
            db.rollback()
            ticket = db.query(Ticket).filter_by(booking_id=booking.id).one()
        else:
            db.refresh(ticket)
    return {
        "code": ticket.code,
        "qr_payload": ticket.qr_payload,
        "booking_ref": booking.booking_ref,
    }


@router.get("/history/list")
def booking_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Booking)
        .filter_by(user_id=user.id, is_synthetic=False)
        .order_by(Booking.id.desc())
        .limit(50)
        .all()
    )
    return {
        "bookings": [
            {
                "booking_ref": b.booking_ref,
                "status": b.status,
                "travel_date": b.travel_date.isoformat(),
                "fare": b.fare,
                "bus_id": b.bus_id,
                "origin": b.bus.origin,
                "destination": b.bus.destination,
                "deadline_time": b.deadline_time.strftime("%H:%M") if b.deadline_time else None,
            }
            for b in rows
        ]
    }


@router.post("/lookup")
def lookup_by_payload(req: PayloadLookupRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ = user
    payload = ticket_service.verify_payload(req.qr_payload)
    if payload is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown ticket payload")
    ticket = (
        db.query(Ticket)
        .filter_by(qr_payload=req.qr_payload)
        .one_or_none()
    )
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown ticket payload")
    return {"code": ticket.code, "booking_ref": payload.get("booking_ref")}


@router.post("/verify")
def verify_ticket(req: VerifyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ = user  # any authenticated user (incl. conductor role later) may scan
    ticket = db.query(Ticket).filter_by(code=req.code.strip().upper()).one_or_none()
    if ticket is None:
        return {"valid": False, "reason": "unknown ticket code"}
    payload = ticket_service.verify_payload(ticket.qr_payload)
    if payload is None:
        return {"valid": False, "reason": "ticket signature invalid (tampered)"}
    booking = db.get(Booking, ticket.booking_id)
    if booking is None or booking.travel_date.isoformat() != payload.get("travel_date"):
        return {"valid": False, "reason": "ticket does not match this trip date"}
    if ticket.used_at is not None:
        return {"valid": False, "reason": "ticket already used"}
    ticket.used_at = datetime.utcnow()
    db.commit()
    return {
        "valid": True,
        "booking_ref": payload["booking_ref"],
        "travel_date": payload["travel_date"],
        "passenger_name": payload["passenger"].get("name"),
    }
