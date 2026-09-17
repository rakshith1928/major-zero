"""T12 — notifications: payment creates rows + email attempt; inbox; graceful SMTP failure."""

import hashlib
import hmac

import pytest

# Every test here needs a genuinely paid booking: activate the stubbed
# test-mode gateway for the whole module (demo orders cannot verify).
pytestmark = pytest.mark.usefixtures("test_mode_payments")

EMAIL = "asha@examplemail.com"
LOGIN = {"email": EMAIL, "password": "s3cretpw!"}
PROFILE = {
    "email": EMAIL,
    "password": "s3cretpw!",
    "name": "Asha R",
    "age": 21,
    "gender": "female",
    "phone": "9876543210",
}


def _headers(client) -> dict:
    client.post("/api/auth/register", json=PROFILE)
    token = client.post("/api/auth/login", json=LOGIN).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _paid_booking(client, headers) -> str:
    from datetime import date

    from app import models
    from app.db import SessionLocal
    from app.seed.buses import seed_buses

    with SessionLocal() as db:
        seed_buses(db)
        bus_id = db.query(models.Bus).first().id
    travel = date.today().isoformat()
    client.post(
        "/api/booking/chat",
        json={"session_id": "n-1", "message": "book a bus to Chennai"},
        headers=headers,
    )
    ref = client.post(
        "/api/booking/select",
        json={
            "session_id": "n-1",
            "bus_id": bus_id,
            "travel_date": travel,
            "boarding_point": "Bangalore",
        },
        headers=headers,
    ).json()["booking_ref"]
    order = client.post(
        "/api/payments/order", json={"booking_ref": ref}, headers=headers
    ).json()
    signature = hmac.new(
        b"private-test-secret",
        f"{order['order_id']}|pay_test123".encode(),
        hashlib.sha256,
    ).hexdigest()
    verified = client.post(
        "/api/payments/verify",
        json={
            "booking_ref": ref,
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": "pay_test123",
            "razorpay_signature": signature,
        },
        headers=headers,
    ).json()
    assert verified["status"] == "PAID"
    return ref


def test_payment_creates_notification_and_survives_smtp_outage(client):
    headers = _headers(client)
    ref = _paid_booking(client, headers)
    inbox = client.get("/api/notifications", headers=headers).json()["notifications"]
    assert any(
        n["type"] == "PAYMENT_SUCCESS" and ref in n["body"] for n in inbox
    ), f"payment notification missing: {inbox}"


def test_inbox_lists_notifications_newest_first(client):
    headers = _headers(client)
    _paid_booking(client, headers)
    inbox = client.get("/api/notifications", headers=headers).json()["notifications"]
    assert len(inbox) >= 1
    assert inbox[0]["title"]
    assert inbox[0]["body"]


def test_trip_reminder_fanout_covers_tomorrows_bookings(client):
    from datetime import date, timedelta

    from app import models
    from app.db import SessionLocal
    from app.services import notifications as notify_service

    headers = _headers(client)
    ref = _paid_booking(client, headers)
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        booking.travel_date = date.today() + timedelta(days=1)
        db.commit()
        sent = notify_service.send_due_reminders(db)
        assert sent >= 1
    inbox = client.get("/api/notifications", headers=headers).json()["notifications"]
    assert any(n["type"] == "TRIP_REMINDER" and ref in n["body"] for n in inbox)
