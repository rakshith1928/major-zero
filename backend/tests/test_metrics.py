"""T13 — metrics harness: timing + manual-field logging per study booking."""

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


def test_study_booking_produces_complete_metric_row(client, session):
    from datetime import date, timedelta

    from app import models
    from app.db import SessionLocal
    from app.seed.buses import seed_buses

    headers = _headers(client)
    sid = "metrics-1"
    start = client.post(
        "/api/metrics/start",
        json={"session_id": sid, "task": "book-ac-sleeper"},
        headers=headers,
    ).json()
    assert start["ok"] is True

    with SessionLocal() as db:
        seed_buses(db)
        bus_id = db.query(models.Bus).first().id
    client.post(
        "/api/booking/chat",
        json={"session_id": sid, "message": "book a bus to Chennai"},
        headers=headers,
    )
    travel = (date.today() + timedelta(days=2)).isoformat()
    created = client.post(
        "/api/booking/select",
        json={
            "session_id": sid,
            "bus_id": bus_id,
            "travel_date": travel,
            "boarding_point": "Bangalore",
            "manual_fields": 0,
        },
        headers=headers,
    ).json()
    done = client.post(
        "/api/metrics/finish",
        json={"session_id": sid, "booking_ref": created["booking_ref"], "success": True},
        headers=headers,
    ).json()
    assert done["booking_seconds"] >= 0
    assert done["manual_fields"] == 0
    assert done["task"] == "book-ac-sleeper"
    assert done["success"] is True
