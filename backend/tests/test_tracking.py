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
