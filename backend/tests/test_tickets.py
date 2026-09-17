"""T07 — QR tickets: issue on payment, verify once, reject duplicates/tampering."""

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
        json={"session_id": "qr-1", "message": "book a bus to Chennai"},
        headers=headers,
    )
    ref = client.post(
        "/api/booking/select",
        json={
            "session_id": "qr-1",
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


def test_paid_booking_issues_qr_ticket(client):
    headers = _headers(client)
    ref = _paid_booking(client, headers)
    ticket = client.get(f"/api/tickets/{ref}", headers=headers).json()
    assert ticket["code"]
    assert ticket["qr_payload"]
    assert ticket["booking_ref"] == ref


def test_conductor_verifies_ticket_once_then_rejects_duplicate(client):
    headers = _headers(client)
    ref = _paid_booking(client, headers)
    ticket = client.get(f"/api/tickets/{ref}", headers=headers).json()

    first = client.post(
        "/api/tickets/verify", json={"code": ticket["code"]}, headers=headers
    ).json()
    assert first["valid"] is True
    assert first["passenger_name"] == "Asha R"

    second = client.post(
        "/api/tickets/verify", json={"code": ticket["code"]}, headers=headers
    ).json()
    assert second["valid"] is False
    assert "already" in second["reason"].lower()


def test_tampered_code_is_rejected(client):
    headers = _headers(client)
    _paid_booking(client, headers)
    response = client.post(
        "/api/tickets/verify", json={"code": "ZZZZ999999"}, headers=headers
    ).json()
    assert response["valid"] is False
    assert "unknown" in response["reason"].lower()


def test_ticket_for_wrong_date_is_rejected(client):
    from datetime import date, timedelta

    from app import models
    from app.db import SessionLocal

    headers = _headers(client)
    ref = _paid_booking(client, headers)
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        booking.travel_date = date.today() + timedelta(days=3)
        db.commit()
    ticket = client.get(f"/api/tickets/{ref}", headers=headers).json()
    response = client.post(
        "/api/tickets/verify", json={"code": ticket["code"]}, headers=headers
    ).json()
    assert response["valid"] is False
    assert "not today" in response["reason"].lower() or "match" in response["reason"].lower()


def test_booking_history_lists_user_bookings(client):
    headers = _headers(client)
    ref = _paid_booking(client, headers)
    body = client.get("/api/tickets/history/list", headers=headers).json()
    assert any(b["booking_ref"] == ref for b in body["bookings"])


def test_lookup_by_payload_returns_code(client):
    headers = _headers(client)
    ref = _paid_booking(client, headers)
    ticket = client.get(f"/api/tickets/{ref}", headers=headers).json()
    found = client.post(
        "/api/tickets/lookup", json={"qr_payload": ticket["qr_payload"]}, headers=headers
    ).json()
    assert found["code"] == ticket["code"]
