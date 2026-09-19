"""Trip Guardian MVP — RED: simulated delay overrides in the tracking service."""

from datetime import date, datetime, time, timedelta

EMAIL = "guardian@examplemail.com"
LOGIN = {"email": EMAIL, "password": "s3cretpw!"}
PROFILE = {
    "email": EMAIL,
    "password": "s3cretpw!",
    "name": "Guardian T",
    "age": 30,
    "gender": "male",
    "phone": "9876543210",
}


def _headers(client) -> dict:
    client.post("/api/auth/register", json=PROFILE)
    token = client.post("/api/auth/login", json=LOGIN).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seeded_booking(session, client, **overrides):
    from app.models import Booking, Bus, User
    from app.seed.buses import seed_buses

    seed_buses(session)
    headers = _headers(client)
    user = session.query(User).filter_by(email=EMAIL).one()
    bus = session.query(Bus).filter_by(origin="Bangalore", destination="Chennai").order_by(Bus.arrival_time).first()
    params = dict(
        user_id=user.id,
        bus_id=bus.id,
        travel_date=date.today() + timedelta(days=1),
        passenger_snapshot_encrypted="enc-test",
        boarding_point="Bangalore",
        fare=bus.base_fare,
        status="PAID",
    )
    params.update(overrides)
    booking = Booking(**params)
    session.add(booking)
    session.commit()
    return booking, bus, headers


def _bus(bus_id=1):
    from types import SimpleNamespace

    return SimpleNamespace(
        id=bus_id,
        origin="Bangalore",
        destination="Chennai",
        departure_time=datetime.now().time(),
        duration_minutes=420,
    )


def test_delay_override_inflates_remaining_and_eta():
    from app.services import tracking as service

    travel = date.today()
    bus = _bus()
    base = service.eta_to_stop(bus, travel, "Chennai")
    service.set_delay(bus.id, 45)
    try:
        delayed = service.eta_to_stop(bus, travel, "Chennai")
        assert delayed["eta_minutes"] == base["eta_minutes"] + 45
        pos = service.position_for(bus, travel)
        assert pos["remaining_minutes"] >= 45
    finally:
        service.clear_delay(bus.id)


def test_clear_delay_restores_schedule():
    from app.services import tracking as service

    travel = date.today()
    bus = _bus()
    base = service.eta_to_stop(bus, travel, "Chennai")
    service.set_delay(bus.id, 30)
    service.clear_delay(bus.id)
    assert service.eta_to_stop(bus, travel, "Chennai") == base


def test_delay_override_zero_or_negative_is_rejected():
    from app.services import tracking as service

    bus = _bus()
    service.set_delay(bus.id, 0)
    service.set_delay(bus.id, -10)
    travel = date.today()
    base = service.eta_to_stop(bus, travel, "Chennai")
    assert service.eta_to_stop(bus, travel, "Chennai") == base


def test_delay_overrides_do_not_leak_between_buses():
    from app.services import tracking as service

    travel = date.today()
    other = _bus(bus_id=999)
    base = service.eta_to_stop(other, travel, "Chennai")
    service.set_delay(12345, 60)
    try:
        assert service.eta_to_stop(other, travel, "Chennai") == base
    finally:
        service.clear_delay(12345)


def test_check_ok_when_arrival_clears_deadline(client, session):
    booking, bus, headers = _seeded_booking(session, client, deadline_time=time(23, 59))
    body = client.post("/api/guardian/check", json={"booking_ref": booking.booking_ref}, headers=headers).json()
    assert body["status"] == "OK"
    assert body["booking_ref"] == booking.booking_ref


def test_check_no_deadline_is_not_watched(client, session):
    booking, bus, headers = _seeded_booking(session, client, deadline_time=None)
    body = client.post("/api/guardian/check", json={"booking_ref": booking.booking_ref}, headers=headers).json()
    assert body["status"] == "NO_DEADLINE"


def test_check_at_risk_after_simulated_delay(client, session):
    from app.services import tracking as service

    booking, bus, headers = _seeded_booking(session, client, deadline_time=time(13, 30))
    # Bus under test arrives mid-day; stage a delay that breaks the deadline.
    service.set_delay(bus.id, 24 * 60)
    try:
        body = client.post("/api/guardian/check", json={"booking_ref": booking.booking_ref}, headers=headers).json()
    finally:
        service.clear_delay(bus.id)
    assert body["status"] == "AT_RISK"
    assert "alternative_bus_id" in body


def test_check_rejects_other_users_booking(client, session):
    booking, bus, headers = _seeded_booking(session, client, deadline_time=time(23, 59))
    other = {"email": "stranger@examplemail.com", "password": "s3cretpw!"}
    client.post("/api/auth/register", json={**PROFILE, "email": other["email"]})
    stranger = client.post("/api/auth/login", json=other).json()["access_token"]
    resp = client.post(
        "/api/guardian/check",
        json={"booking_ref": booking.booking_ref},
        headers={"Authorization": f"Bearer {stranger}"},
    )
    assert resp.status_code == 404


def test_rebook_copies_passenger_and_supersedes(client, session):
    from app.models import Booking, Bus

    booking, bus, headers = _seeded_booking(session, client, deadline_time=time(23, 59))
    alt = session.query(Bus).filter(
        Bus.origin == "Bangalore", Bus.destination == "Chennai", Bus.id != bus.id
    ).order_by(Bus.arrival_time).first()
    body = client.post(
        "/api/guardian/rebook",
        json={"booking_ref": booking.booking_ref, "bus_id": alt.id},
        headers=headers,
    ).json()
    assert body["booking_ref"] != booking.booking_ref
    session.expire_all()
    assert session.get(Booking, booking.id).status == "SUPERSEDED"
    new = session.query(Booking).filter_by(booking_ref=body["booking_ref"]).one()
    assert new.passenger_snapshot_encrypted == "enc-test"
    assert new.deadline_time == booking.deadline_time
    assert new.status == "PENDING_PAYMENT"


def test_simulate_delay_endpoint_sets_and_clears(client, session):
    from app.seed.buses import seed_buses
    from app.services import tracking as service

    seed_buses(session)
    headers = _headers(client)
    from app.models import Bus

    bus = session.query(Bus).first()
    client.post("/api/guardian/simulate-delay", json={"bus_id": bus.id, "minutes": 45}, headers=headers)
    assert service.delay_for(bus.id) == 45
    client.post("/api/guardian/simulate-delay", json={"bus_id": bus.id, "minutes": 0}, headers=headers)
    assert service.delay_for(bus.id) == 0


def test_guardian_requires_auth(client, session):
    booking, bus, headers = _seeded_booking(session, client, deadline_time=time(23, 59))
    assert client.post("/api/guardian/check", json={"booking_ref": booking.booking_ref}).status_code in (401, 403)


def test_history_lists_route_for_repeat_booking(client, session):
    booking, bus, headers = _seeded_booking(session, client, deadline_time=time(23, 59))
    body = client.get("/api/tickets/history/list", headers=headers).json()
    entry = next(b for b in body["bookings"] if b["booking_ref"] == booking.booking_ref)
    assert entry["origin"] == "Bangalore"
    assert entry["destination"] == "Chennai"
    assert entry["deadline_time"] == "23:59"
    assert entry["bus_id"] == bus.id


def test_chat_repeat_intent_rebooks_frequent_route(client, session):
    booking, bus, headers = _seeded_booking(session, client, deadline_time=time(23, 59))
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": "repeat-1", "message": "same as last time"},
        headers=headers,
    ).json()
    assert reply["slots"].get("origin") == "Bangalore"
    assert reply["slots"].get("destination") == "Chennai"
    # No self/other cue in the message, so the flow asks who the ticket is
    # for; confirming completes the repeat booking with buses listed.
    assert reply["state"] == "NEEDS_INFO"
    follow = client.post(
        "/api/booking/chat",
        json={"session_id": "repeat-1", "message": "for me"},
        headers=headers,
    ).json()
    assert follow.get("buses"), "expected confirmed repeat intent to return buses"
