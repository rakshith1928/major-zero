"""T10 — simulated GPS: positions advance, ETA consistent, simulation disclosed."""

from datetime import date, timedelta


def test_positions_endpoint_lists_buses_with_coordinates(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    body = client.get("/api/tracking/positions").json()
    assert body["simulated"] is True
    assert body["buses"], "expected live positions for seeded buses"
    for entry in body["buses"]:
        assert -90 <= entry["lat"] <= 90
        assert -180 <= entry["lon"] <= 180
        assert entry["progress"] is not None
        assert 0.0 <= entry["progress"] <= 1.0


def test_eta_to_boarding_point_is_consistent_with_schedule(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    travel = (date.today() + timedelta(days=1)).isoformat()
    positions = client.get("/api/tracking/positions").json()["buses"]
    bus_id = positions[0]["bus_id"]
    body = client.get(
        "/api/tracking/eta",
        params={"bus_id": bus_id, "travel_date": travel, "stop": "Bangalore"},
    ).json()
    assert body["bus_id"] == bus_id
    assert "eta_minutes" in body
    assert body["eta_minutes"] >= 0


def test_tracking_requires_no_auth(client):
    # Public map: passengers check buses without logging in.
    assert client.get("/api/tracking/positions").status_code == 200


def test_eta_unknown_stop_is_422_with_corridor_hint(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    travel = (date.today() + timedelta(days=1)).isoformat()
    positions = client.get("/api/tracking/positions").json()["buses"]
    bus_id = positions[0]["bus_id"]
    resp = client.get(
        "/api/tracking/eta",
        params={"bus_id": bus_id, "travel_date": travel, "stop": "Nowhere"},
    )
    assert resp.status_code == 422
    hint = resp.json()["detail"]
    assert "Vellore" in hint["stops"] or "Chennai" in hint["stops"]


def test_eta_to_origin_reports_departure_not_zero(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    # Tomorrow: every bus is still SCHEDULED regardless of wall-clock time.
    travel = (date.today() + timedelta(days=1)).isoformat()
    positions = client.get("/api/tracking/positions").json()["buses"]
    bus_id = positions[0]["bus_id"]
    body = client.get(
        "/api/tracking/eta",
        params={"bus_id": bus_id, "travel_date": travel, "stop": "Bangalore"},
    ).json()
    assert body["detail"] == "departs_in"
    assert body["eta_minutes"] > 0


def test_eta_completed_bus_says_arrived(client, session):
    from datetime import datetime
    from app.seed.buses import seed_buses

    seed_buses(session)
    from app.models import Bus
    from app.services import tracking as service

    bus = session.query(Bus).order_by(Bus.departure_time).first()
    past = datetime.combine(date.today(), bus.departure_time) + timedelta(
        minutes=bus.duration_minutes + 30
    )
    assert service.position_for(bus, date.today(), now=past)["status"] == "COMPLETED"
    assert service.eta_to_stop(bus, date.today(), bus.destination, now=past)["detail"] == "completed"
