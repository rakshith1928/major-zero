"""Fare copilot — deterministic cheapest-date comparison for a route.

Numbers first: every figure in the response comes from the seeded inventory
and demand model. An LLM sentence is attempted only as polish (OpenRouter
free router); any failure falls back to the deterministic template, so the
figures a traveller sees are never model-hallucinated.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Bus

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def next_weekday(from_date: date, weekday: int) -> date:
    delta = (weekday - from_date.weekday()) % 7
    return from_date + timedelta(days=delta or 7)


def mentioned_dates(message: str, today: date, limit: int = 4) -> list[date]:
    """Weekday names in the message, resolved to upcoming dates (deduped)."""
    import re

    found: list[date] = []
    for name, weekday in WEEKDAYS.items():
        if re.search(rf"\b{name}\b", message or "", re.IGNORECASE):
            day = next_weekday(today, weekday)
            if day not in found:
                found.append(day)
    return found[:limit]


def compare_dates(
    db: Session, origin: str, destination: str, dates: list[date], bus_type: str | None = None
) -> dict:
    options = []
    for travel in dates:
        query = db.query(Bus).filter(
            Bus.origin.ilike(origin), Bus.destination.ilike(destination)
        )
        if bus_type:
            query = query.filter(Bus.bus_type == bus_type)
        buses = query.order_by(Bus.base_fare).all()
        if buses:
            cheapest = buses[0]
            options.append(
                {
                    "date": travel.isoformat(),
                    "min_fare": cheapest.base_fare,
                    "buses": len(buses),
                    "cheapest_operator": cheapest.operator,
                    "cheapest_departure": cheapest.departure_time.strftime("%H:%M"),
                }
            )
        else:
            options.append({"date": travel.isoformat(), "min_fare": None, "buses": 0})
    ranked = sorted(
        [o for o in options if o["min_fare"] is not None],
        key=lambda o: o["min_fare"],
    )
    return {"options": options, "cheapest": ranked[0] if ranked else None}


def template_summary(comparison: dict) -> str:
    options = [o for o in comparison["options"] if o["min_fare"] is not None]
    if not options:
        return "No buses run on those dates for this route."
    cheapest = comparison["cheapest"]
    dearest = max(options, key=lambda o: o["min_fare"])
    if cheapest["date"] == dearest["date"]:
        return f"All options bottom out at Rs.{cheapest['min_fare']} on {cheapest['date']}."
    saving = dearest["min_fare"] - cheapest["min_fare"]
    detail = ""
    if cheapest.get("cheapest_operator") and cheapest.get("cheapest_departure"):
        detail = f" ({cheapest['cheapest_operator']}, {cheapest['cheapest_departure']})"
    return (
        f"Leave {cheapest['date']} — from Rs.{cheapest['min_fare']}{detail}, "
        f"Rs.{saving} less than {dearest['date']} at Rs.{dearest['min_fare']}."
    )


def summarize(options: list[dict], api_key: str = "", model: str = "openrouter/free") -> str:
    """One-sentence takeaway; deterministic template unless an LLM key works."""
    comparison = {
        "options": options,
        "cheapest": next((o for o in sorted(
            [o for o in options if o.get("min_fare") is not None],
            key=lambda o: o["min_fare"],
        )), None),
    }
    fallback = template_summary(comparison)
    if not api_key:
        return fallback
    try:
        import httpx

        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "Reply with exactly one short sentence stating the cheapest option. Use only the numbers given. No extra advice.",
                    },
                    {"role": "user", "content": f"Fare options: {options}. {fallback}"},
                ],
            },
            timeout=6,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return content.strip() if isinstance(content, str) and content.strip() else fallback
    except Exception:
        return fallback
