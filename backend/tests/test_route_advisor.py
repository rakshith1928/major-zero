"""Route advisor — RED: ranked best-bus recommendations per corridor."""

from datetime import date


def test_routes_ranks_earliest_arrival_first(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    body = client.get(
        "/api/tracking/routes",
        params={"origin": "Bangalore", "destination": "Chennai"},
    ).json()
    assert body["simulated"] is True
    assert len(body["buses"]) >= 2
    # Absolute ordering: arrival_day_offset breaks ties string sorting misses.
    absolute = [
        b["arrival_day_offset"] * 24 * 60 + int(b["arrival"][:2]) * 60 + int(b["arrival"][3:])
        for b in body["buses"]
    ]
    assert absolute == sorted(absolute)
    assert body["recommended_bus_id"] == body["buses"][0]["bus_id"]
    assert "Earliest arrival" in body["reason"]


def test_routes_prefers_deadline_clearing_bus(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    body = client.get(
        "/api/tracking/routes",
        params={"origin": "Bangalore", "destination": "Chennai", "deadline": "23:59"},
    ).json()
    assert body["recommended_bus_id"] in [b["bus_id"] for b in body["buses"]]
    assert "23:59" in body["reason"]


def test_routes_admits_when_nothing_beats_the_deadline(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    body = client.get(
        "/api/tracking/routes",
        params={"origin": "Bangalore", "destination": "Chennai", "deadline": "00:01"},
    ).json()
    assert "misses" in body["reason"]


def test_routes_empty_corridor_explains_itself(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    body = client.get(
        "/api/tracking/routes",
        params={"origin": "Nowhere", "destination": "Noland"},
    ).json()
    assert body["buses"] == []
    assert body["recommended_bus_id"] is None


def test_routes_are_public(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    # No auth header: travellers compare routes freely, like positions.
    assert client.get("/api/tracking/routes", params={"origin": "Bangalore", "destination": "Hyderabad"}).status_code == 200
    _ = date
