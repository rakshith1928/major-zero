"""Stub extractor hardening — RED: weekdays, next week, airport codes."""

from datetime import date, timedelta


def _extract(message: str, slots=None):
    from app.services.extractor import StubSlotExtractor

    return StubSlotExtractor().extract(message, slots or {})


def test_weekday_name_resolves_to_upcoming_date():
    out = _extract("Bangalore to Chennai on Friday")
    assert "travel_date" in out
    travel = date.fromisoformat(out["travel_date"])
    assert travel.weekday() == 4  # Friday
    assert 1 <= (travel - date.today()).days <= 7


def test_next_week_means_plus_seven_days():
    out = _extract("Bangalore to Chennai next week")
    assert out.get("travel_date") == (date.today() + timedelta(days=7)).isoformat()


def test_this_weekend_meens_saturday():
    out = _extract("Chennai to Bangalore this weekend")
    travel = date.fromisoformat(out["travel_date"])
    assert travel.weekday() == 5  # Saturday
    assert 1 <= (travel - date.today()).days <= 7


def test_explicit_date_beats_weekday():
    # "Friday 25/12" must keep the exact date, not the weekday.
    out = _extract("Bangalore to Chennai Friday 25/12")
    year = date.today().year
    assert out.get("travel_date") == date(year, 12, 25).isoformat()


def test_airport_codes_resolve_to_cities():
    out = _extract("blr to maa tomorrow")
    assert out.get("origin") == "Bangalore"
    assert out.get("destination") == "Chennai"


def test_hyd_code_resolves():
    out = _extract("Bangalore to hyd tomorrow")
    assert out.get("destination") == "Hyderabad"
