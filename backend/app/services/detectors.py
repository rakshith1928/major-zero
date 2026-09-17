"""T06 — Pre-Booking Mistake Predictor detectors (pure functions).

Each detector takes plain data and returns either None (no warning) or a
warning dict {code, message}. The booking router persists outcomes to
warnings_log (T06 acceptance: fired / accepted / overridden).
"""

from collections import Counter
from datetime import date, datetime, time


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def deadline_buffer(deadline: time | None, bus, travel_date) -> dict | None:
    """Fire when the arrival leaves too thin a margin before the deadline."""
    if deadline is None:
        return None
    arrival_minutes = _minutes(bus.arrival_time)
    # Arrival is on travel day + offset; deadline is on arrival day.
    margin = _minutes(deadline) - arrival_minutes
    arrival_str = bus.arrival_time.strftime("%H:%M")
    if margin < 0:
        return {
            "code": "ARRIVES_AFTER_DEADLINE",
            "message": (
                f"This bus arrives at {arrival_str}, which is after your "
                f"{deadline.strftime('%H:%M')} deadline. Pick an earlier bus?"
            ),
            "margin_minutes": margin,
        }
    if margin < 45:
        return {
            "code": "THIN_BUFFER",
            "message": (
                f"This bus arrives at {arrival_str}, leaving only {margin} minutes "
                f"before your {deadline.strftime('%H:%M')} deadline. "
                "Would you like a safer option?"
            ),
            "margin_minutes": margin,
        }
    return None


def boarding_deviation(chosen: str, history: list[str], route) -> dict | None:
    """Fire when the chosen boarding point breaks the user's route habit."""
    if not history:
        return None
    usual, count = Counter(history).most_common(1)[0]
    if chosen.strip().lower() == usual.strip().lower():
        return None
    if count < 2:
        return None
    return {
        "code": "UNUSUAL_BOARDING_POINT",
        "message": (
            f"You usually board at {usual} on "
            f"{route[0]} → {route[1]}, but chose {chosen}. Please confirm."
        ),
        "usual": usual,
    }


def passenger_mismatch(passenger: dict, passenger_ref: str, bus_type: str) -> dict | None:
    """Fire on passenger/seat-rule inconsistencies (age, gender policy)."""
    age = passenger.get("age")
    try:
        age = int(age)
    except (TypeError, ValueError):
        return {
            "code": "PASSENGER_AGE_UNKNOWN",
            "message": "I could not verify the passenger's age against berth rules.",
        }
    if bus_type == "AC_SLEEPER" and age < 5:
        return {
            "code": "CHILD_IN_SLEEPER",
            "message": (
                "Children under 5 cannot occupy a sleeper berth alone. "
                "Please check the berth rules or pick a seater."
            ),
        }
    if age > 100:
        return {
            "code": "PASSENGER_AGE_IMPLAUSIBLE",
            "message": f"Age {age} looks wrong — please confirm the passenger's age.",
        }
    return None


def date_time_errors(travel_date, raw_text: str, bus) -> list[dict]:
    """Flag past dates and overnight-arrival confusion."""
    warnings: list[dict] = []
    today = date.today()
    if isinstance(travel_date, datetime):
        travel_date = travel_date.date()
    if travel_date < today:
        warnings.append(
            {
                "code": "PAST_DATE",
                "message": (
                    f"{travel_date.isoformat()} is in the past. "
                    "Which date did you mean?"
                ),
            }
        )
    text = (raw_text or "").lower()
    if getattr(bus, "arrival_day_offset", 0) >= 1 and any(
        word in text for word in ["morning", "am", "a.m.", "arriv", "reach", "tomorrow"]
    ):
        warnings.append(
            {
                "code": "OVERNIGHT_ARRIVAL",
                "message": (
                    "Note: this is an overnight bus — arrival is the morning "
                    "AFTER departure. Please confirm the date works for you."
                ),
            }
        )
    return warnings
