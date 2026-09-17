"""T08 — payment endpoints: order creation + signature verification."""

import threading

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import Booking, Payment, User
from app.services.payments import deterministic_fake_order_id, get_gateway

router = APIRouter(prefix="/api/payments", tags=["payments"])

# FastAPI runs sync endpoints on a threadpool, so two overlapping POST /order
# calls for one booking can interleave between the SELECT and the INSERT.
# This per-process lock serializes gateway order minting + row insertion.
# Bounded guarantee: it protects a single uvicorn process (this project's
# SQLite dev/demo deployment); multi-worker/multi-host deployments would need
# a database-level unique constraint instead.
_order_lock = threading.Lock()


class OrderRequest(BaseModel):
    booking_ref: str


class VerifyRequest(BaseModel):
    booking_ref: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def _own_booking(db: Session, user_id: int, ref: str) -> Booking:
    booking = (
        db.query(Booking).filter_by(booking_ref=ref, user_id=user_id).one_or_none()
    )
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown booking")
    return booking


def _order_response(booking: Booking, payment: Payment) -> dict:
    gateway = get_gateway()
    response = {
        "order_id": payment.order_id,
        "amount": payment.amount,
        "currency": "INR",
        "booking_ref": booking.booking_ref,
        # Explicit checkout contract: the frontend opens the demo sheet for a
        # demo order and the real Razorpay sheet only for a test-mode order.
        # A demo order never carries (or implies) a gateway key.
        "checkout_mode": gateway.checkout_mode,
    }
    if gateway.checkout_mode == "razorpay_test":
        response["key_id"] = gateway.key_id
    return response


@router.post("/order")
def create_order(req: OrderRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = _own_booking(db, user.id, req.booking_ref)
    try:
        gateway = get_gateway()
    except ValueError:
        # Misconfigured gateway (live key or missing test keys) must never
        # reach the network: fail closed before any row or key is exposed.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "payment gateway is not configured for test mode",
        )
    with _order_lock:
        # Re-read under the lock: a concurrent verify may have paid this
        # booking between the query above and acquiring the lock.
        db.refresh(booking)
        if booking.status == "PAID":
            raise HTTPException(status.HTTP_409_CONFLICT, "booking already paid")
        # Reuse the still-open CREATED order across retries so one booking
        # never accumulates duplicate rows. The query itself drops rows that
        # no longer qualify (FAILED verification, changed fare); the mode
        # check decides whether any survivor is still ours to reuse:
        #   - demo gateway: reuse only the row carrying the deterministic
        #     fake id for this booking (never an externally minted id);
        #   - real gateway: ids come from Razorpay, so reuse only a row this
        #     real gateway minted and never the fake id.
        fake_id = deterministic_fake_order_id(booking.booking_ref)
        open_rows = (
            db.query(Payment)
            .filter_by(booking_id=booking.id, status="CREATED", amount=booking.fare)
            .order_by(Payment.id.desc())
            .all()
        )
        payment = next(
            (p for p in open_rows if (p.order_id == fake_id) == (gateway.checkout_mode == "demo")),
            None,
        )
        if payment is None:
            try:
                order = gateway.create_order(booking.booking_ref, booking.fare)
            except ValueError:
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "payment gateway is not configured for test mode",
                )
            payment = Payment(
                booking_id=booking.id,
                order_id=order["order_id"],
                amount=order["amount"],
                status="CREATED",
            )
            db.add(payment)
            db.commit()
    return _order_response(booking, payment)


@router.post("/verify")
def verify(req: VerifyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = _own_booking(db, user.id, req.booking_ref)
    try:
        gateway = get_gateway()
    except ValueError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "payment gateway is not configured for test mode",
        )
    if gateway.checkout_mode == "demo" or req.razorpay_order_id == deterministic_fake_order_id(booking.booking_ref):
        # Demo checkout is non-transactional: nothing verifies, nothing mutates.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "demo orders cannot be verified")
    with _order_lock:
        db.refresh(booking)
        payment = (
            db.query(Payment).populate_existing()
            .filter_by(booking_id=booking.id, order_id=req.razorpay_order_id)
            .order_by(Payment.id.desc())
            .first()
        )
        if payment is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown order")
        if payment.status == "SUCCESS":
            if (
                payment.payment_id != req.razorpay_payment_id
                or payment.signature != req.razorpay_signature
                or not gateway.verify_signature(
                    req.razorpay_order_id, req.razorpay_payment_id, req.razorpay_signature
                )
            ):
                raise HTTPException(status.HTTP_409_CONFLICT, "payment replay does not match")
            return {"status": booking.status, "booking_ref": booking.booking_ref}
        if booking.status == "PAID":
            raise HTTPException(status.HTTP_409_CONFLICT, "booking already paid")
        if payment.status != "CREATED":
            raise HTTPException(status.HTTP_409_CONFLICT, "order is not open")
        newer_order = db.query(Payment).filter(
            Payment.booking_id == booking.id, Payment.id > payment.id
        ).first()
        if newer_order is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "order has been superseded")
        # A superseded order (fare changed since it was minted) must not pay
        # for the booking at the old price.
        if payment.amount != booking.fare:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "order amount does not match the current fare"
            )
        if not gateway.verify_signature(
            req.razorpay_order_id, req.razorpay_payment_id, req.razorpay_signature
        ):
            payment.status = "FAILED"
            db.commit()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "signature verification failed")
        payment.payment_id = req.razorpay_payment_id
        payment.signature = req.razorpay_signature
        payment.status = "SUCCESS"
        booking.status = "PAID"
        db.flush()
        # Issue the ticket NOW so the notification carries the real code + link.
        from app.models import Ticket
        from app.services import tickets as ticket_service
        from app.services import vault as vault_service

        details = vault_service.decrypt_for_user(user.id, booking.passenger_snapshot_encrypted, db, booking.passenger_profile_id, "POST /api/payments/verify")
        ticket = Ticket(
            booking_id=booking.id,
            qr_payload=ticket_service.sign_payload(
                {
                    "booking_ref": booking.booking_ref,
                    "bus_id": booking.bus_id,
                    "travel_date": booking.travel_date.isoformat(),
                    "passenger": details,
                }
            ),
        )
        db.add(ticket)
        db.flush()
        from app.services import notifications as notify_service

        notify_service.payment_succeeded(
            db,
            user,
            booking,
            ticket_code=ticket.code,
            ticket_link=f"/tickets?ref={booking.booking_ref}",
        )
        db.commit()
    return {"status": booking.status, "booking_ref": booking.booking_ref}
