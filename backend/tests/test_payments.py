"""T08 — Razorpay test-mode payments through the HTTP seam.

All databases are in-memory; outbound payment HTTP is stubbed.
"""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app import models
from app.db import SessionLocal
from app.services import payments as payment_service

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


@pytest.fixture(autouse=True)
def isolated_gateway(monkeypatch):
    monkeypatch.setattr(payment_service, "_gateway", payment_service.FakeGateway())
    monkeypatch.setattr(payment_service.settings, "razorpay_key_id", "")
    monkeypatch.setattr(payment_service.settings, "razorpay_key_secret", "")
    # requests is optional/missing in this environment. Stub its import boundary
    # rather than install it or allow any payment request to leave the process.
    post = Mock(side_effect=AssertionError("unexpected outbound payment request"))
    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(post=post))
    return post


@pytest.fixture
def razorpay_http(isolated_gateway, monkeypatch):
    monkeypatch.setattr(payment_service.settings, "razorpay_key_id", "rzp_test_public123")
    monkeypatch.setattr(payment_service.settings, "razorpay_key_secret", "private-test-secret")

    def respond(url, *, auth, json, timeout):
        assert url == "https://api.razorpay.com/v1/orders"
        assert auth == ("rzp_test_public123", "private-test-secret")
        assert timeout == 15
        assert json["currency"] == "INR"
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "id": f"order_external{isolated_gateway.call_count}",
                "amount": json["amount"],
                "currency": "INR",
            },
        )

    isolated_gateway.side_effect = respond
    payment_service.set_gateway(payment_service.RazorpayGateway())
    return isolated_gateway


def _headers(client) -> dict:
    client.post("/api/auth/register", json=PROFILE)
    token = client.post("/api/auth/login", json=LOGIN).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _prepayment_booking(client, headers) -> str:
    from datetime import date, timedelta

    from app.seed.buses import seed_buses

    with SessionLocal() as db:
        seed_buses(db)
        bus = db.query(models.Bus).first()
        bus_id = bus.id
    travel = (date.today() + timedelta(days=2)).isoformat()
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": "pay-1", "message": "book a bus to Chennai"},
        headers=headers,
    )
    assert reply.status_code == 200
    created = client.post(
        "/api/booking/select",
        json={
            "session_id": "pay-1",
            "bus_id": bus_id,
            "travel_date": travel,
            "boarding_point": "Bangalore",
        },
        headers=headers,
    ).json()
    assert created["status"] == "PENDING_PAYMENT"
    return created["booking_ref"]


def _order(client, headers, ref):
    response = client.post(
        "/api/payments/order", json={"booking_ref": ref}, headers=headers
    )
    assert response.status_code == 200
    return response.json()


def _rows(ref):
    with SessionLocal() as db:
        return (
            db.query(models.Payment)
            .join(models.Booking)
            .filter(models.Booking.booking_ref == ref)
            .order_by(models.Payment.id)
            .all()
        )


def _verify(client, headers, ref, order, signature="valid-for-tests", payment_id="pay_test123"):
    return client.post(
        "/api/payments/verify",
        json={
            "booking_ref": ref,
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        },
        headers=headers,
    )


def _hmac_signature(order_id: str, payment_id: str) -> str:
    import hashlib
    import hmac

    return hmac.new(
        b"private-test-secret", f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()


def test_checkout_creates_order_for_prepayment_booking(client):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    assert order["order_id"].startswith("order_")
    assert order["amount"] > 0
    assert order["booking_ref"] == ref


def test_verifying_valid_signature_marks_booking_paid(client, razorpay_http):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    verified = _verify(client, headers, ref, order, _hmac_signature(order["order_id"], "pay_test123")).json()
    assert verified["status"] == "PAID"


def test_forged_signature_is_rejected(client, razorpay_http):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    response = _verify(client, headers, ref, order, signature="forged")
    assert response.status_code == 400
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        assert booking.status == "PENDING_PAYMENT"


def test_demo_order_cannot_be_verified(client):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    assert order["checkout_mode"] == "demo"
    response = _verify(client, headers, ref, order, signature="valid-for-tests")
    assert response.status_code == 400
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        assert booking.status == "PENDING_PAYMENT"
        row = db.query(models.Payment).filter_by(booking_id=booking.id).one()
        assert row.status == "CREATED"
        assert db.query(models.Ticket).filter_by(booking_id=booking.id).count() == 0
    ticket_response = client.get(f"/api/tickets/{ref}", headers=headers)
    assert ticket_response.status_code == 409
    assert ticket_response.json() == {"detail": "booking is not paid yet"}


def test_repeated_successful_verification_is_idempotent(client, razorpay_http):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    sig = _hmac_signature(order["order_id"], "pay_test123")
    assert _verify(client, headers, ref, order, sig).json()["status"] == "PAID"
    again = _verify(client, headers, ref, order, sig)
    assert again.status_code == 200
    assert again.json()["status"] == "PAID"
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        assert len(db.query(models.Ticket).filter_by(booking_id=booking.id).all()) == 1
        assert db.query(models.Notification).filter_by(type="PAYMENT_SUCCESS").count() == 1


def test_forged_verify_after_success_never_demotes_payment(client, razorpay_http):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    assert _verify(client, headers, ref, order, _hmac_signature(order["order_id"], "pay_test123")).json()["status"] == "PAID"
    forged = _verify(client, headers, ref, order, signature="forged")
    assert forged.status_code == 409
    with SessionLocal() as db:
        payment = db.query(models.Payment).one()
        assert payment.status == "SUCCESS"
        assert db.query(models.Booking).filter_by(booking_ref=ref).one().status == "PAID"


def test_stale_amount_order_cannot_verify(client, razorpay_http):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    stale = _order(client, headers, ref)
    with SessionLocal() as db:
        row = db.query(models.Booking).filter_by(booking_ref=ref).one()
        row.fare += 500
        db.commit()
    second = _order(client, headers, ref)
    assert second["order_id"] != stale["order_id"]
    response = _verify(client, headers, ref, stale, _hmac_signature(stale["order_id"], "pay_test123"))
    assert response.status_code == 409
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        assert booking.status == "PENDING_PAYMENT"
        assert db.query(models.Payment).filter_by(booking_id=booking.id).count() == 2


def test_demo_order_cannot_verify_after_gateway_switch(client, request):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    demo = _order(client, headers, ref)
    # Only NOW is a (stubbed) real gateway configured; the demo order minted
    # earlier must stay non-transactional regardless of the current gateway.
    request.getfixturevalue("razorpay_http")
    response = _verify(client, headers, ref, demo, signature="valid-for-tests")
    assert response.status_code == 400
    assert _rows(ref)[0].status == "CREATED"


def test_payment_endpoints_are_scoped_to_the_booking_owner(client):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    client.post("/api/auth/register", json={**PROFILE, "email": "other@examplemail.com"})
    intruder_token = client.post(
        "/api/auth/login",
        json={"email": "other@examplemail.com", "password": PROFILE["password"]},
    ).json()["access_token"]
    intruder = {"Authorization": f"Bearer {intruder_token}"}
    assert client.post("/api/payments/order", json={"booking_ref": ref}, headers=intruder).status_code == 404
    assert _verify(client, intruder, ref, order).status_code == 404


def test_payment_endpoints_reject_unauthenticated_calls(client):
    response_order = client.post("/api/payments/order", json={"booking_ref": "X"})
    response_verify = client.post("/api/payments/verify", json={"booking_ref": "X", "razorpay_order_id": "o", "razorpay_payment_id": "p", "razorpay_signature": "s"})
    assert response_order.status_code == 401
    assert response_verify.status_code == 401


def test_demo_response_omits_key_even_when_test_key_is_configured(client, monkeypatch):
    monkeypatch.setattr(payment_service.settings, "razorpay_key_id", "rzp_test_unused")
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    assert order["checkout_mode"] == "demo"
    assert "key_id" not in order
    assert "key_secret" not in order


def test_test_response_exposes_only_configured_public_key(client, razorpay_http):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    assert order == {
        "order_id": "order_external1",
        "amount": _rows(ref)[0].amount,
        "currency": "INR",
        "booking_ref": ref,
        "checkout_mode": "razorpay_test",
        "key_id": "rzp_test_public123",
    }
    assert razorpay_http.call_args.kwargs["json"] == {
        "amount": order["amount"] * 100, "currency": "INR", "receipt": ref,
    }


@pytest.mark.parametrize("real_test_gateway", [False, True])
def test_sequential_retries_reuse_one_created_row(client, request, real_test_gateway):
    http = request.getfixturevalue("razorpay_http") if real_test_gateway else None
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    first = _order(client, headers, ref)
    for _ in range(2):
        assert _order(client, headers, ref) == first
    assert len(_rows(ref)) == 1
    if http is not None:
        assert http.call_count == 1


def test_gateway_switch_replaces_fake_order_not_reused_by_test_gateway(client, request):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    demo = _order(client, headers, ref)
    http = request.getfixturevalue("razorpay_http")
    real = _order(client, headers, ref)
    assert real["order_id"] == "order_external1"
    assert real["order_id"] != demo["order_id"]
    assert real["checkout_mode"] == "razorpay_test"
    row_count = len(_rows(ref))
    assert _order(client, headers, ref) == real
    assert len(_rows(ref)) == row_count
    assert http.call_count == 1
    # Switching back must never label an external order as a demo order.
    payment_service.set_gateway(payment_service.FakeGateway())
    assert _order(client, headers, ref) == demo
    assert len(_rows(ref)) == row_count


@pytest.mark.parametrize("changed", ["FAILED", "amount"])
def test_ineligible_order_is_not_reused(client, razorpay_http, changed):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    first = _order(client, headers, ref)
    with SessionLocal() as db:
        payment = db.query(models.Payment).one()
        if changed == "amount":
            payment.amount += 1
        else:
            payment.status = changed
        db.commit()
    second = _order(client, headers, ref)
    assert second["order_id"] != first["order_id"]
    assert _order(client, headers, ref) == second
    assert len(_rows(ref)) == 2
    assert razorpay_http.call_count == 2
    if changed == "FAILED":
        assert _rows(ref)[0].status == "FAILED"


@pytest.mark.parametrize("key_id,secret", [
    ("rzp_live_forbidden", "secret"),
    ("not-a-test-key", "secret"),
    ("rzp_test_", "secret"),
    ("", "secret"),
    ("rzp_test_public123", ""),
])
def test_invalid_gateway_configuration_is_rejected(key_id, secret, isolated_gateway):
    with pytest.raises(ValueError, match="test-mode"):
        payment_service.RazorpayGateway(key_id=key_id, key_secret=secret)
    isolated_gateway.assert_not_called()


@pytest.mark.parametrize("entrypoint", ["get_gateway", "use_live_gateway_if_configured"])
@pytest.mark.parametrize("secret", ["secret", ""])
def test_factory_rejects_live_configuration_even_without_secret(monkeypatch, entrypoint, secret):
    monkeypatch.setattr(payment_service, "_gateway", None)
    monkeypatch.setattr(payment_service.settings, "razorpay_key_id", "rzp_live_forbidden")
    monkeypatch.setattr(payment_service.settings, "razorpay_key_secret", secret)
    with pytest.raises(ValueError, match="test-mode"):
        getattr(payment_service, entrypoint)()


def test_bad_configuration_returns_503_without_creating_payment(client, monkeypatch):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    monkeypatch.setattr(payment_service, "_gateway", None)
    monkeypatch.setattr(payment_service.settings, "razorpay_key_id", "rzp_live_forbidden")
    monkeypatch.setattr(payment_service.settings, "razorpay_key_secret", "do-not-expose")
    response = client.post("/api/payments/order", json={"booking_ref": ref}, headers=headers)
    assert response.status_code == 503
    assert "do-not-expose" not in response.text
    assert _rows(ref) == []


def test_paid_booking_rejected_without_new_rows(client):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    _order(client, headers, ref)
    with SessionLocal() as db:
        db.query(models.Booking).filter_by(booking_ref=ref).one().status = "PAID"
        db.commit()
    response = client.post("/api/payments/order", json={"booking_ref": ref}, headers=headers)
    assert response.status_code == 409
    assert len(_rows(ref)) == 1


def test_overlapping_order_calls_in_one_process_reuse_one_order(client, razorpay_http):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from app.api.payments import OrderRequest, create_order

    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    with SessionLocal() as db:
        user = db.query(models.User).filter_by(email=EMAIL).one()
    entered = Event()
    release = Event()
    second_started = Event()
    original = razorpay_http.side_effect

    def slow_response(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    razorpay_http.side_effect = slow_response

    def call_order(started=None):
        with SessionLocal() as db:
            if started:
                started.set()
            return create_order(OrderRequest(booking_ref=ref), user=user, db=db)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(call_order)
        try:
            assert entered.wait(5)
            second = pool.submit(call_order, second_started)
            assert second_started.wait(5)
            # A second HTTP call proves the critical section was not protected.
            # Give that worker time to enter; production should hold it at the lock.
            from time import sleep
            sleep(0.1)
        finally:
            release.set()
        assert first.result(timeout=5) == second.result(timeout=5)
    assert razorpay_http.call_count == 1
    assert len(_rows(ref)) == 1


def test_verify_rejects_superseded_order_after_fare_change(client, razorpay_http):
    # Supersession by fare change, not by Payment.amount tampering: the stale
    # order still carries the old minted amount while the booking now costs more.
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    stale = _order(client, headers, ref)
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        booking.fare += 500
        db.commit()
    second = _order(client, headers, ref)
    assert second["order_id"] != stale["order_id"]
    response = _verify(client, headers, ref, stale, _hmac_signature(stale["order_id"], "pay_test123"))
    assert response.status_code == 409
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        assert booking.status == "PENDING_PAYMENT"
        rows = db.query(models.Payment).filter_by(booking_id=booking.id).all()
        assert len(rows) == 2
        assert next(p for p in rows if p.order_id == stale["order_id"]).status == "CREATED"


def test_verify_rejects_already_paid_booking_for_other_order(client, razorpay_http):
    # A stray CREATED row must not pay an already-paid booking.
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    first = _order(client, headers, ref)
    assert _verify(client, headers, ref, first, _hmac_signature(first["order_id"], "pay_test123")).json()["status"] == "PAID"
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        db.add(models.Payment(booking_id=booking.id, order_id="order_stale123", amount=booking.fare, status="CREATED"))
        db.commit()
    response = _verify(client, headers, ref, {"order_id": "order_stale123"}, _hmac_signature("order_stale123", "pay_test123"))
    assert response.status_code == 409
    with SessionLocal() as db:
        booking = db.query(models.Booking).filter_by(booking_ref=ref).one()
        other = db.query(models.Payment).filter_by(order_id="order_stale123").one()
        assert other.status == "CREATED"
        assert db.query(models.Ticket).filter_by(booking_id=booking.id).count() == 1


def test_verify_of_unknown_order_is_rejected_without_rows(client, razorpay_http):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    _order(client, headers, ref)
    response = _verify(client, headers, ref, {"order_id": "order_missing"}, _hmac_signature("order_missing", "pay_test123"))
    assert response.status_code == 404
    assert len(_rows(ref)) == 1


@pytest.mark.parametrize("waiting_endpoint", ["order", "verify"])
def test_concurrent_verify_refreshes_waiting_session(client, razorpay_http, monkeypatch, waiting_endpoint):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from fastapi import HTTPException
    from app.api import payments as api

    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    loaded, release = Event(), Event()
    own_booking = api._own_booking

    def pause_after_load(*args):
        booking = own_booking(*args)
        loaded.set()
        assert release.wait(5)
        return booking

    monkeypatch.setattr(api, "_own_booking", pause_after_load)

    def waiting_call():
        with SessionLocal() as db:
            user = db.query(models.User).filter_by(email=EMAIL).one()
            # Keep stale Payment in the identity map as well as Booking.
            payment = db.query(models.Payment).one()
            if waiting_endpoint == "order":
                with pytest.raises(HTTPException) as error:
                    api.create_order(api.OrderRequest(booking_ref=ref), user=user, db=db)
                assert error.value.status_code == 409
            else:
                result = api.verify(api.VerifyRequest(
                    booking_ref=ref, razorpay_order_id=order["order_id"],
                    razorpay_payment_id="pay_test123",
                    razorpay_signature=_hmac_signature(order["order_id"], "pay_test123"),
                ), user=user, db=db)
                assert result["status"] == "PAID"
                assert payment.status == "SUCCESS"

    with ThreadPoolExecutor(max_workers=1) as pool:
        with api._order_lock:
            pending = pool.submit(waiting_call)
            assert loaded.wait(5)
            monkeypatch.setattr(api, "_own_booking", own_booking)
        try:
            assert _verify(client, headers, ref, order, _hmac_signature(order["order_id"], "pay_test123")).status_code == 200
        finally:
            release.set()
        pending.result(timeout=5)
    assert len(_rows(ref)) == 1
    with SessionLocal() as db:
        assert db.query(models.Ticket).count() == 1
        assert db.query(models.Notification).filter_by(type="PAYMENT_SUCCESS").count() == 1


@pytest.mark.parametrize("state", ["FAILED", "superseded", "demo_gateway"])
def test_ineligible_verification_is_nonmutating(client, razorpay_http, state):
    headers = _headers(client)
    ref = _prepayment_booking(client, headers)
    order = _order(client, headers, ref)
    with SessionLocal() as db:
        payment = db.query(models.Payment).one()
        if state == "FAILED":
            payment.status = "FAILED"
        elif state == "superseded":
            db.add(models.Payment(booking_id=payment.booking_id, order_id="order_newer", amount=payment.amount, status="CREATED"))
        db.commit()
    if state == "demo_gateway":
        payment_service.set_gateway(payment_service.FakeGateway())
    before = [(p.status, p.payment_id, p.signature) for p in _rows(ref)]
    response = _verify(client, headers, ref, order, _hmac_signature(order["order_id"], "pay_test123"))
    assert response.status_code == (400 if state == "demo_gateway" else 409)
    assert [(p.status, p.payment_id, p.signature) for p in _rows(ref)] == before
    with SessionLocal() as db:
        assert db.query(models.Booking).one().status == "PENDING_PAYMENT"
        assert db.query(models.Ticket).count() == 0
        assert db.query(models.Notification).count() == 0
