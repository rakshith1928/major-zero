"""T03 — chat booking through the HTTP seam.

The SlotExtractor seam is stubbed with canned JSON (no network in tests).
"""

from datetime import date, timedelta

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


def _token(client) -> str:
    client.post("/api/auth/register", json=PROFILE)
    return client.post("/api/auth/login", json=LOGIN).json()["access_token"]


def _headers(client) -> dict:
    return {"Authorization": f"Bearer {_token(client)}"}


TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def test_search_returns_matching_ac_sleeper_buses(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    headers = _headers(client)
    body = client.post(
        "/api/booking/search",
        json={
            "origin": "Bangalore",
            "destination": "Chennai",
            "travel_date": TOMORROW,
            "bus_type": "AC_SLEEPER",
        },
        headers=headers,
    ).json()
    assert body["buses"], "expected AC sleeper buses Bangalore->Chennai"
    for bus in body["buses"]:
        assert bus["origin"] == "Bangalore"
        assert bus["destination"] == "Chennai"
        assert bus["bus_type"] == "AC_SLEEPER"
        assert 600 <= bus["fare"] <= 1400
        assert bus["total_seats"] > 0


def test_chat_turn_extracts_slots_and_asks_for_deadline(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    headers = _headers(client)
    reply = client.post(
        "/api/booking/chat",
        json={
            "session_id": "chat-deadline-1",
            "message": "Book an AC sleeper from Bangalore to Chennai tomorrow for me",
        },
        headers=headers,
    ).json()
    assert reply["slots"]["origin"] == "Bangalore"
    assert reply["slots"]["destination"] == "Chennai"
    assert reply["state"] in ("NEEDS_INFO", "RESULTS")
    # The assistant proactively asks for an arrival deadline (T03 requirement).
    combined = (
        (reply.get("assistant_text") or "")
        + " "
        + " ".join(m.get("content", "") for m in reply.get("messages", []))
    ).lower()
    assert "deadline" in combined or "reach" in combined


def test_chat_turn_with_deadline_records_deadline_time(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    headers = _headers(client)
    session_id = "chat-deadline-2"
    client.post(
        "/api/booking/chat",
        json={
            "session_id": session_id,
            "message": "Book an AC sleeper from Bangalore to Chennai tomorrow for me",
        },
        headers=headers,
    )
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": session_id, "message": "I must reach by 8 AM"},
        headers=headers,
    ).json()
    assert reply["slots"].get("deadline_time") == "08:00"


def test_selecting_a_bus_creates_pending_booking_with_self_passenger(
    client, session
):
    from app.seed.buses import seed_buses

    seed_buses(session)
    headers = _headers(client)
    reply = client.post(
        "/api/booking/chat",
        json={
            "session_id": "chat-select-1",
            "message": "Book an AC sleeper from Bangalore to Chennai tomorrow for me",
        },
        headers=headers,
    ).json()
    assert reply["buses"], "expected bus results to select from"
    bus_id = reply["buses"][0]["id"]

    created = client.post(
        "/api/booking/select",
        json={
            "session_id": "chat-select-1",
            "bus_id": bus_id,
            "travel_date": TOMORROW,
            "boarding_point": "Bangalore",
        },
        headers=headers,
    ).json()
    assert created["status"] == "PENDING_PAYMENT"
    assert created["passenger"]["name"] == "Asha R", "self booking must autofill vault"
    assert created["booking_ref"]

    # State machine persisted: a fresh history read shows pre-payment state.
    history = client.get(
        "/api/booking/session/chat-select-1", headers=headers
    ).json()
    assert history["state"] == "PRE_PAYMENT"
    assert history["booking_ref"] == created["booking_ref"]


def test_chat_requires_authentication(client):
    response = client.post(
        "/api/booking/chat",
        json={"session_id": "anon", "message": "hello"},
    )
    assert response.status_code == 401
