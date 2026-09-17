"""T09 — demand prediction API, crowd levels, fare indicator."""

from datetime import date, timedelta


def test_demand_curve_returns_daily_values_with_peak_flags(client, session):
    from app.seed.buses import seed_buses
    from app.seed.history import seed_history

    seed_buses(session)
    seed_history(session)
    travel = (date.today() + timedelta(days=7)).isoformat()
    body = client.get(
        "/api/analytics/demand",
        params={"origin": "Bangalore", "destination": "Chennai", "date": travel},
    ).json()
    assert body["route"] == ["Bangalore", "Chennai"]
    assert len(body["curve"]) >= 1
    for point in body["curve"]:
        assert 0.0 <= point["predicted_occupancy"] <= 1.0
        assert isinstance(point["is_peak"], bool)
    assert any(p["is_peak"] for p in body["curve"])


def test_search_cards_carry_crowd_level_and_fare_indicator(client, session):
    from app.seed.buses import seed_buses
    from app.seed.history import seed_history

    seed_buses(session)
    seed_history(session)
    client.post(
        "/api/auth/register",
        json={
            "email": "asha@examplemail.com",
            "password": "s3cretpw!",
            "name": "Asha R",
            "age": 21,
            "gender": "female",
            "phone": "9876543210",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "asha@examplemail.com", "password": "s3cretpw!"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    travel = (date.today() + timedelta(days=7)).isoformat()
    buses = client.post(
        "/api/booking/search",
        json={
            "origin": "Bangalore",
            "destination": "Chennai",
            "travel_date": travel,
        },
        headers=headers,
    ).json()["buses"]
    assert buses
    for bus in buses:
        assert 0.0 <= bus["crowd_level"] <= 1.0
        assert bus["fare_indicator"] in ("LOW", "NORMAL", "HIGH")
