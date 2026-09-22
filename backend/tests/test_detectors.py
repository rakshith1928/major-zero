"""T06 — the four Mistake Predictor detectors as pure functions."""

from datetime import date, time, timedelta
from types import SimpleNamespace

from app.services.detectors import (
    boarding_deviation,
    date_time_errors,
    deadline_buffer,
    passenger_mismatch,
)


def _bus(dep="22:30", arr="06:30", offset=1):
    dep_h, dep_m = map(int, dep.split(":"))
    arr_h, arr_m = map(int, arr.split(":"))
    return SimpleNamespace(
        departure_time=time(dep_h, dep_m),
        arrival_time=time(arr_h, arr_m),
        arrival_day_offset=offset,
    )


def test_deadline_buffer_fires_on_thin_margin():
    warning = deadline_buffer(
        deadline=time(8, 0), bus=_bus(arr="07:50"), travel_date=date(2026, 9, 20)
    )
    assert warning is not None
    assert "7:50" in warning["message"] or "07:50" in warning["message"]


def test_deadline_buffer_quiet_on_comfortable_margin():
    assert (
        deadline_buffer(
            deadline=time(12, 0), bus=_bus(arr="06:30"), travel_date=date(2026, 9, 20)
        )
        is None
    )


def test_deadline_buffer_fires_when_bus_arrives_after_deadline():
    assert (
        deadline_buffer(
            deadline=time(7, 0), bus=_bus(arr="07:50"), travel_date=date(2026, 9, 20)
        )
        is not None
    )


def test_boarding_deviation_fires_on_unusual_point():
    history = ["Majestic", "Majestic", "Majestic", "Majestic"]
    warning = boarding_deviation(
        chosen="Electronic City", history=history, route=("Bangalore", "Chennai")
    )
    assert warning is not None
    assert "Majestic" in warning["message"]


def test_boarding_deviation_quiet_on_usual_point_or_no_history():
    assert (
        boarding_deviation(
            chosen="Majestic",
            history=["Majestic", "Majestic"],
            route=("Bangalore", "Chennai"),
        )
        is None
    )
    assert (
        boarding_deviation(chosen="Anywhere", history=[], route=("Bangalore", "Chennai"))
        is None
    )


def test_passenger_mismatch_fires_on_child_in_sleeper():
    warning = passenger_mismatch(
        passenger={"age": 4, "gender": "male"}, passenger_ref="self", bus_type="AC_SLEEPER"
    )
    assert warning is not None


def test_passenger_mismatch_quiet_on_consistent_adult():
    assert (
        passenger_mismatch(
            passenger={"age": 21, "gender": "female"},
            passenger_ref="self",
            bus_type="AC_SLEEPER",
        )
        is None
    )


def test_date_time_errors_fires_on_past_date():
    warnings = date_time_errors(
        travel_date=date(2020, 1, 1), raw_text="book for yesterday", bus=_bus()
    )
    assert any(w["code"] == "PAST_DATE" for w in warnings)


def test_date_time_errors_flags_overnight_arrival_date():
    warnings = date_time_errors(
        travel_date=date(2026, 9, 20),
        raw_text="reaching tomorrow morning 6 AM",
        bus=_bus(arr="06:30", offset=1),
    )
    assert any(w["code"] == "OVERNIGHT_ARRIVAL" for w in warnings)


def test_date_time_errors_quiet_on_clean_future_trip():
    # Relative date: a hardcoded "future" date rots into the past.
    future = date.today() + timedelta(days=30)
    assert (
        date_time_errors(
            travel_date=future,
            raw_text="travelling next week",
            bus=_bus(arr="18:00", offset=0),
        )
        == []
    )
