"""Slot-extraction seam (ADR-004).

`SlotExtractor` is the interface the booking flow programs against.
`StubSlotExtractor` returns canned JSON for tests (no network).
`GeminiSlotExtractor` will call the live API in production (T03+, needs key).
"""

import re
from datetime import date, timedelta
from typing import Protocol


class SlotExtractor(Protocol):
    def extract(self, message: str, session_slots: dict) -> dict:
        ...


_DATE_WORDS = {
    "today": 0,
    "tonight": 0,
    "tomorrow": 1,
    "day after tomorrow": 2,
}

_BUS_TYPES = {
    "ac sleeper": "AC_SLEEPER",
    "a/c sleeper": "AC_SLEEPER",
    "sleeper": "AC_SLEEPER",
    "semi sleeper": "AC_SEMI_SLEEPER",
    "semi-sleeper": "AC_SEMI_SLEEPER",
    "non-ac": "NON_AC_SEATER",
    "non ac": "NON_AC_SEATER",
    "seater": "NON_AC_SEATER",
}

# Minimal known-place list keeps the stub deterministic; production Gemini
# handles arbitrary places.
_PLACES = ["bangalore", "bengaluru", "chennai", "hyderabad", "madras"]


def _norm_place(raw: str) -> str:
    raw = raw.strip().lower()
    if raw in ("bengaluru",):
        return "Bangalore"
    if raw in ("madras",):
        return "Chennai"
    return raw.title()


class StubSlotExtractor:
    """Deterministic rule-based extractor: good enough for tests and offline demo."""

    def extract(self, message: str, session_slots: dict) -> dict:
        text = message.lower()
        slots = dict(session_slots)

        from_match = re.search(r"from\s+([a-z\s]+?)(?:\s+to\s+|\s*$)", text)
        to_match = re.search(r"to\s+([a-z\s]+?)(?:\s+(?:tomorrow|today|tonight|day|on|by|before|after|ac|a\/c|non|for|my|me|i)\b|\s*$)", text)
        if from_match:
            place = from_match.group(1).strip()
            if place in _PLACES or " " not in place:
                slots["origin"] = _norm_place(place)
        if to_match:
            place = to_match.group(1).strip()
            if place in _PLACES or " " not in place:
                slots["destination"] = _norm_place(place)

        # "Bangalore to Chennai" without leading "from" — take known place before "to".
        if "origin" not in slots and "destination" in slots:
            before_to = text.split("to", 1)[0]
            for known in _PLACES:
                if re.search(rf"\b{re.escape(known)}\b", before_to):
                    slots["origin"] = _norm_place(known)
                    break

        # Bare reply to "Where are you travelling from?" / "Where to?" — e.g. just "Bangalore".
        stripped = text.strip()
        if stripped in _PLACES:
            if "origin" not in slots:
                slots["origin"] = _norm_place(stripped)
            elif "destination" not in slots:
                slots["destination"] = _norm_place(stripped)

        for word, offset in _DATE_WORDS.items():
            if word in text:
                slots["travel_date"] = (
                    date.today() + timedelta(days=offset)
                ).isoformat()
                break
        date_match = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", text)
        if date_match and "travel_date" not in slots:
            day, month = int(date_match.group(1)), int(date_match.group(2))
            year = int(date_match.group(3)) if date_match.group(3) else date.today().year
            if year < 100:
                year += 2000
            try:
                slots["travel_date"] = date(year, month, day).isoformat()
            except ValueError:
                pass  # impossible date like 31/02: ask the user instead

        for phrase, bus_type in _BUS_TYPES.items():
            if phrase in text:
                slots["bus_type"] = bus_type
                break

        budget = re.search(r"(?:below|under|budget|less than|rs\.?|₹)\s*(\d{3,5})", text)
        if budget:
            slots["budget"] = int(budget.group(1))

        deadline = re.search(
            r"(?:reach|arrive|by|before|starts?\s+at|exam(?:\s+starts?)?(?:\s+at)?)\s+(?:by\s+|at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
            text,
        )
        if deadline or "must reach" in text or "exam" in text:
            if deadline:
                hour = int(deadline.group(1))
                minute = int(deadline.group(2) or 0)
                meridiem = deadline.group(3)
                if meridiem == "pm" and hour < 12:
                    hour += 12
                if meridiem == "am" and hour == 12:
                    hour = 0
                slots["deadline_time"] = f"{hour:02d}:{minute:02d}"
            else:
                slots.setdefault("deadline_time", None)

        if re.search(r"\b(for|my)\s+(mother|mom|father|dad|wife|husband|son|daughter|brother|sister|friend|colleague|parents?)\b", text):
            slots["passenger_ref"] = "other"
        elif re.search(r"\bfor\s+me\b|\bfor\s+myself\b|\bmy\s+ticket\b", text):
            slots["passenger_ref"] = "self"

        return slots


_extractor: SlotExtractor = StubSlotExtractor()


def get_extractor() -> SlotExtractor:
    return _extractor


def set_extractor(extractor: SlotExtractor) -> None:
    global _extractor
    _extractor = extractor
