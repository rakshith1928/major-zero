"""Safest-pick ranking — RED: margin-first bus choice for chat results."""

from datetime import date


def _card(**over):
    base = {
        "id": 1, "operator": "X", "bus_type": "AC_SLEEPER",
        "departure": "22:30", "arrival": "06:10", "arrival_day_offset": 1,
        "duration_minutes": 460, "fare": 1200, "total_seats": 36,
        "seats_left": 10, "crowd_level": 0.5, "fare_indicator": "MEDIUM",
    }
    base.update(over)
    return base


def test_deadline_picks_biggest_buffer():
    from app.services import safety

    travel = date(2026, 9, 20)
    buses = [
        _card(id=1, arrival="07:50", arrival_day_offset=1, crowd_level=0.2),
        _card(id=2, arrival="06:10", arrival_day_offset=1, crowd_level=0.8),
    ]
    assert safety.safest(buses, "08:00", travel)["id"] == 2


def test_no_deadline_picks_calmest_then_earliest():
    from app.services import safety

    travel = date(2026, 9, 20)
    buses = [
        _card(id=1, departure="06:00", arrival="13:00", arrival_day_offset=0, crowd_level=0.9),
        _card(id=2, departure="07:30", arrival="14:00", arrival_day_offset=0, crowd_level=0.3),
        _card(id=3, departure="09:00", arrival="15:30", arrival_day_offset=0, crowd_level=0.3),
    ]
    assert safety.safest(buses, None, travel)["id"] == 2


def test_empty_list_has_no_safest():
    from app.services import safety

    assert safety.safest([], "08:00", date(2026, 9, 20)) is None


def test_chat_marks_safest_bus(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    from tests.test_booking import _headers

    headers = _headers(client)
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": "safe-1", "message": "Bangalore to Chennai tomorrow for me"},
        headers=headers,
    ).json()
    assert reply.get("buses")
    calmest = min(reply["buses"], key=lambda b: (b["crowd_level"], b["departure"]))
    assert reply.get("safest_bus_id") == calmest["id"]
