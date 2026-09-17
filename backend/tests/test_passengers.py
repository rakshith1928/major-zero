"""T05 — other-passenger capture + opt-in memory, all through chat + API."""

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


def _start_other_flow(client, headers, session_id="t05-mom"):
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": session_id, "message": "Book a ticket for my mother"},
        headers=headers,
    ).json()
    assert reply["slots"].get("passenger_ref") == "other"
    return session_id


def test_capture_conversation_collects_details_without_forms(client):
    headers = _headers(client)
    sid = _start_other_flow(client, headers)
    body = client.post(
        "/api/booking/passenger/capture",
        json={
            "session_id": sid,
            "name": "Lakshmi R",
            "age": 55,
            "gender": "female",
            "phone": "9812345678",
        },
        headers=headers,
    ).json()
    assert body["passenger"]["name"] == "Lakshmi R"
    assert body["needs_consent"] is True


def test_declining_consent_leaves_no_trace(client, session):
    from app.models import PassengerProfile

    headers = _headers(client)
    sid = _start_other_flow(client, headers, "t05-decline")
    client.post(
        "/api/booking/passenger/capture",
        json={
            "session_id": sid,
            "name": "Lakshmi R",
            "age": 55,
            "gender": "female",
            "phone": "9812345678",
        },
        headers=headers,
    )
    body = client.post(
        "/api/booking/passenger/consent",
        json={"session_id": sid, "remember": False},
        headers=headers,
    ).json()
    assert body["remembered"] is False
    others = (
        session.query(PassengerProfile).filter_by(is_self=False).all()
    )
    assert others == []


def test_consent_stores_encrypted_profile_with_view_and_delete(client, session):
    from app.models import PassengerProfile

    headers = _headers(client)
    sid = _start_other_flow(client, headers, "t05-keep")
    client.post(
        "/api/booking/passenger/capture",
        json={
            "session_id": sid,
            "name": "Lakshmi R",
            "age": 55,
            "gender": "female",
            "phone": "9812345678",
        },
        headers=headers,
    )
    body = client.post(
        "/api/booking/passenger/consent",
        json={"session_id": sid, "remember": True, "label": "Mother"},
        headers=headers,
    ).json()
    assert body["remembered"] is True

    profiles = client.get("/api/passengers", headers=headers).json()["passengers"]
    assert any(p["label"] == "Mother" for p in profiles)
    stored = session.query(PassengerProfile).filter_by(is_self=False).one()
    assert "Lakshmi" not in stored.data_encrypted

    profile_id = next(p["id"] for p in profiles if p["label"] == "Mother")
    assert (
        client.delete(f"/api/passengers/{profile_id}", headers=headers).status_code
        == 204
    )
    assert session.query(PassengerProfile).filter_by(is_self=False).all() == []


def test_saved_passenger_enables_zero_form_reuse(client):
    from datetime import date, timedelta

    from app import models
    from app.db import SessionLocal
    from app.seed.buses import seed_buses

    headers = _headers(client)
    sid = _start_other_flow(client, headers, "t05-reuse")
    client.post(
        "/api/booking/passenger/capture",
        json={
            "session_id": sid,
            "name": "Lakshmi R",
            "age": 55,
            "gender": "female",
            "phone": "9812345678",
        },
        headers=headers,
    )
    client.post(
        "/api/booking/passenger/consent",
        json={"session_id": sid, "remember": True, "label": "Mother"},
        headers=headers,
    )
    profile_id = next(
        p["id"]
        for p in client.get("/api/passengers", headers=headers).json()["passengers"]
        if p["label"] == "Mother"
    )
    with SessionLocal() as db:
        seed_buses(db)
        bus_id = db.query(models.Bus).first().id
    travel = (date.today() + timedelta(days=2)).isoformat()
    created = client.post(
        "/api/booking/select",
        json={
            "session_id": sid,
            "bus_id": bus_id,
            "travel_date": travel,
            "boarding_point": "Bangalore",
            "passenger_profile_id": profile_id,
        },
        headers=headers,
    ).json()
    assert created["passenger"]["name"] == "Lakshmi R"
