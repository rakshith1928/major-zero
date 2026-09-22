"""Fare copilot MVP — RED: deterministic date comparison + chat intent."""

from datetime import date, timedelta


def test_compare_dates_ranks_cheapest_first(client, session):
    from app.seed.buses import seed_buses
    from app.services import fare_advice

    seed_buses(session)
    dates = [date.today() + timedelta(days=i + 1) for i in range(3)]
    result = fare_advice.compare_dates(session, "Bangalore", "Chennai", dates)
    assert len(result["options"]) == 3
    fares = [o["min_fare"] for o in result["options"]]
    assert fares == sorted(fares)
    assert result["cheapest"]["date"] == result["options"][0]["date"]
    assert result["cheapest"]["min_fare"] <= result["options"][-1]["min_fare"]


def test_compare_dates_empty_route_has_no_cheapest(client, session):
    from app.services import fare_advice

    result = fare_advice.compare_dates(session, "Nowhere", "Noland", [date.today() + timedelta(days=1)])
    assert result["options"][0]["min_fare"] is None
    assert result["cheapest"] is None


def test_summarize_falls_back_to_template_without_key():
    from datetime import date as date_cls

    from app.services import fare_advice

    options = [
        {"date": "2026-09-25", "min_fare": 780, "buses": 10},
        {"date": "2026-09-24", "min_fare": 1150, "buses": 10},
    ]
    text = fare_advice.summarize(options, api_key="")
    assert "2026-09-25" in text and "780" in text
    assert isinstance(text, str) and len(text) > 0
    _ = date_cls


def test_summarize_falls_back_when_llm_times_out(monkeypatch):
    import httpx

    from app.services import fare_advice

    def slow(*args, **kwargs):
        raise httpx.TimeoutException("server took too long")

    monkeypatch.setattr(httpx, "post", slow)
    options = [
        {"date": "2026-09-25", "min_fare": 780, "buses": 10},
        {"date": "2026-09-24", "min_fare": 1150, "buses": 10},
    ]
    text = fare_advice.summarize(options, api_key="sk-or-test")
    assert "2026-09-25" in text and "780" in text


def test_chat_compare_intent_returns_fare_advice(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    from tests.test_booking import _headers

    headers = _headers(client)
    client.post(
        "/api/booking/chat",
        json={"session_id": "fare-1", "message": "AC sleeper from Bangalore to Chennai"},
        headers=headers,
    )
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": "fare-1", "message": "which day is cheapest, Friday or Saturday?"},
        headers=headers,
    ).json()
    assert reply["state"] == "RESULTS"
    comp = reply.get("fare_comparison")
    assert comp and len(comp["options"]) >= 2
    assert reply["slots"]["travel_date"] == comp["cheapest"]["date"]
    assert reply.get("buses"), "cheapest date buses keep the booking flow going"
