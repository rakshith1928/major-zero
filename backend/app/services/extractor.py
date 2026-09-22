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
_PLACES = [
    "bangalore", "bengaluru", "blr", "chennai", "madras", "maa",
    "hyderabad", "hyd", "mysuru", "mysore", "coimbatore", "vijayawada",
]

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _norm_place(raw: str) -> str:
    raw = raw.strip().lower()
    if raw in ("bengaluru", "blr"):
        return "Bangalore"
    if raw in ("madras", "maa"):
        return "Chennai"
    if raw in ("hyd",):
        return "Hyderabad"
    if raw in ("mysore",):
        return "Mysuru"
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

        # Weekday names, "next week", "weekend" — explicit dates above win.
        if "travel_date" not in slots:
            for name, weekday in _WEEKDAYS.items():
                if re.search(rf"\b{name}\b", text):
                    delta = (weekday - date.today().weekday()) % 7
                    slots["travel_date"] = (
                        date.today() + timedelta(days=delta or 7)
                    ).isoformat()
                    break
        if "travel_date" not in slots and re.search(r"\bnext week\b", text):
            slots["travel_date"] = (date.today() + timedelta(days=7)).isoformat()
        if "travel_date" not in slots and re.search(r"\bweekend\b", text):
            delta = (5 - date.today().weekday()) % 7
            slots["travel_date"] = (
                date.today() + timedelta(days=delta or 7)
            ).isoformat()

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


class OpenRouterSlotExtractor:
    """LLM slot extraction via OpenRouter (OpenAI-compatible), stub fallback.

    - No key -> pure stub (offline tests, free Render without key).
    - Any network/parse error -> stub result, never raises.
    - Valid LLM keys overlay stub slots (origin/destination normalized).
    """

    _ALLOWED = ("origin", "destination", "travel_date", "bus_type", "budget", "deadline_time")
    _REQUIRED = ("origin", "destination", "travel_date")

    def __init__(self, api_key: str = "", model: str = "openrouter/free", http_post=None, timeout: int = 4):
        self.api_key = api_key or ""
        self.model = model
        self.http_post = http_post
        self.timeout = timeout
        self._stub = StubSlotExtractor()

    def extract(self, message: str, session_slots: dict) -> dict:
        stub_slots = self._stub.extract(message, session_slots)
        if not self.api_key:
            return stub_slots
        if self._rules_resolved(stub_slots):
            return stub_slots
        try:
            if self.http_post is not None:
                data = self.http_post(message, dict(stub_slots))
            else:
                data = self._call_api(message, dict(stub_slots))
            if not isinstance(data, dict):
                return stub_slots
            merged = dict(stub_slots)
            for key in self._ALLOWED:
                value = data.get(key)
                if value is None or value == "":
                    continue
                if not isinstance(value, (str, int, float, bool)):
                    continue  # objects/arrays would render as [object Object]
                if key in ("origin", "destination") and isinstance(value, str):
                    merged[key] = _norm_place(value)
                else:
                    merged[key] = value
            return merged
        except Exception:
            return stub_slots

    def _rules_resolved(self, stub_slots: dict) -> bool:
        """True when a network round-trip can add nothing: the route and date
        are known and who the ticket is for is settled. Follow-ups like
        "for me" then answer instantly from rules alone."""
        if any(not stub_slots.get(key) for key in self._REQUIRED):
            return False
        return stub_slots.get("passenger_ref") not in (None, "ambiguous")

    def _call_api(self, message: str, session_slots: dict) -> dict:
        import json as _json

        import httpx

        system = (
            "Extract bus-booking slots as JSON only. Keys: origin, destination, "
            "travel_date (YYYY-MM-DD), bus_type, budget (number), deadline_time (HH:MM). "
            "Omit unknown keys. No markdown, no commentary."
        )
        payload = {
            "model": self.model,
            "max_tokens": 200,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Known slots: {_json.dumps(session_slots)} Message: {message}",
                },
            ],
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://college-project-c6b6a.web.app",
            "X-Title": "ZeroBus",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            body = resp.json()
        content = body["choices"][0]["message"]["content"]
        if isinstance(content, str):
            text = content.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if "\n" in text:
                    text = text.split("\n", 1)[1]
                    if text.lower().startswith("json"):
                        text = text[4:].lstrip()
            return _json.loads(text)
        return {}


_extractor: SlotExtractor = StubSlotExtractor()


def get_extractor() -> SlotExtractor:
    try:
        from app.config import settings as _settings

        key = getattr(_settings, "openrouter_api_key", "")
        model = getattr(_settings, "openrouter_model", "openrouter/free")
        if key and isinstance(_extractor, StubSlotExtractor):
            return OpenRouterSlotExtractor(api_key=key, model=model)
    except Exception:
        pass
    return _extractor


def set_extractor(extractor: SlotExtractor) -> None:
    global _extractor
    _extractor = extractor
