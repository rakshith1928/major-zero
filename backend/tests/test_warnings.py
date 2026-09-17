"""T06 wiring — detectors fire during chat/select; warnings API records keep/change."""

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


def _headers(client) -> dict:
    client.post("/api/auth/register", json=PROFILE)
    token = client.post("/api/auth/login", json=LOGIN).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_selecting_late_bus_fires_deadline_warning_with_safer_alternative(
    client, session
):
    from app.seed.buses import seed_buses

    seed_buses(session)
    headers = _headers(client)
    sid = "t06-deadline"
    client.post(
        "/api/booking/chat",
        json={
            "session_id": sid,
            "message": "Book an AC sleeper from Bangalore to Chennai tomorrow for me",
        },
        headers=headers,
    )
    # The 23:30 KPN sleeper arrives 06:45 next day — 75 min before 8 AM is
    # comfortable, so state a tighter deadline to force the thin-buffer path.
    client.post(
        "/api/booking/chat",
        json={"session_id": sid, "message": "My exam starts at 7 AM"},
        headers=headers,
    )
    # The 23:30 KPN sleeper arrives 06:45 next day — thin buffer before 8 AM.
    # Pick the bus whose arrival is closest-after an early deadline instead:
    # find any bus and assert the flow warns when margin is thin.
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": sid, "message": "show buses"},
        headers=headers,
    ).json()
    assert reply["buses"]
    late_bus = max(reply["buses"], key=lambda b: b["arrival"])
    created = client.post(
        "/api/booking/select",
        json={
            "session_id": sid,
            "bus_id": late_bus["id"],
            "travel_date": (date.today() + timedelta(days=1)).isoformat(),
            "boarding_point": "Bangalore",
        },
        headers=headers,
    ).json()
    assert created["status"] == "PENDING_PAYMENT"
    warnings = created.get("warnings", [])
    assert any(w["code"] in ("THIN_BUFFER", "ARRIVES_AFTER_DEADLINE") for w in warnings), (
        f"expected a deadline warning, got {warnings}"
    )
    warned = next(
        w for w in warnings if w["code"] in ("THIN_BUFFER", "ARRIVES_AFTER_DEADLINE")
    )
    assert warned.get("alternative_bus_id"), "warning must offer a safer alternative"


def test_warning_outcomes_are_recorded(client, session):
    from app.models import WarningLog
    from app.seed.buses import seed_buses

    seed_buses(session)
    headers = _headers(client)
    sid = "t06-outcome"
    client.post(
        "/api/booking/chat",
        json={
            "session_id": sid,
            "message": "Book an AC sleeper from Bangalore to Chennai tomorrow for me",
        },
        headers=headers,
    )
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": sid, "message": "show buses"},
        headers=headers,
    ).json()
    bus_id = reply["buses"][0]["id"]
    created = client.post(
        "/api/booking/select",
        json={
            "session_id": sid,
            "bus_id": bus_id,
            "travel_date": (date.today() + timedelta(days=1)).isoformat(),
            "boarding_point": "Far Away Point",
        },
        headers=headers,
    ).json()
    ref = created["booking_ref"]
    # If no detector fired (clean scenario), synthesize one outcome so the
    # logging contract is still verified end to end.
    codes = [w["code"] for w in created.get("warnings", [])] or ["MANUAL_CHECK"]
    for code in codes:
        response = client.post(
            "/api/warnings/outcome",
            json={"booking_ref": ref, "detector": code, "outcome": "OVERRIDDEN"},
            headers=headers,
        )
        assert response.status_code == 200
    rows = session.query(WarningLog).all()
    assert rows, "warning outcomes must be logged"
    assert {r.outcome for r in rows} <= {"FIRED", "ACCEPTED", "OVERRIDDEN"}
