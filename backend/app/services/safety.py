"""Safest pick — margin-first bus choice for chat results.

With a deadline: the detector-clean bus with the biggest arrival buffer
(latest arrival still comfortably before the deadline wins nothing — the
earliest comfortable arrival does). Without: calmest bus, then earliest
departure. Pure schedule math on the cards the search already built.
"""

from datetime import date


def _arrival_minutes(card: dict) -> int:
    hh, mm = card["arrival"].split(":")
    return card.get("arrival_day_offset", 0) * 24 * 60 + int(hh) * 60 + int(mm)


def _deadline_minutes(deadline: str) -> int:
    hh, mm = deadline.split(":")
    return int(hh) * 60 + int(mm)


def safest(buses: list[dict], deadline: str | None, travel: date) -> dict | None:
    """Return the winning bus card, or None for an empty list."""
    _ = travel  # cards already carry day offsets; kept for signature symmetry
    if not buses:
        return None
    if deadline:
        limit = _deadline_minutes(deadline)
        clearing = [b for b in buses if _arrival_minutes(b) <= limit]
        pool = clearing or buses
        return max(pool, key=lambda b: limit - _arrival_minutes(b))
    return min(buses, key=lambda b: (b.get("crowd_level", 1), b.get("departure", "99:99")))
