"""Requirement Negotiator — compromise suggestions when no bus fits.

When an exact search is empty, constraints are relaxed in an order that
preserves what the traveller asked for: budget first (keeps the bus type),
then bus type, then both. Returns the dropped constraint names plus the
relaxed slot values so the caller can re-search and continue booking on the
compromise directly — one tap, no retyping.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.models import Bus


def _count(
    db: Session, origin: str, destination: str, bus_type: str | None, budget: int | None
) -> int:
    query = db.query(Bus).filter(
        Bus.origin.ilike(origin), Bus.destination.ilike(destination)
    )
    if bus_type:
        query = query.filter(Bus.bus_type == bus_type)
    if budget is not None:
        query = query.filter(Bus.base_fare <= budget)
    return query.count()


def relax_search(
    db: Session,
    origin: str,
    destination: str,
    travel: date,
    bus_type: str | None = None,
    budget: int | None = None,
) -> dict | None:
    """Return a compromise plan, or None when exact search suffices or nothing helps."""
    _ = travel  # inventory is a daily template; relaxation is about constraints
    if _count(db, origin, destination, bus_type, budget) > 0:
        return None
    plans = [
        (["budget"], bus_type, None),
        (["bus_type"], None, budget),
        (["budget", "bus_type"], None, None),
    ]
    for dropped, relaxed_type, relaxed_budget in plans:
        if "budget" in dropped and budget is None:
            continue  # nothing to relax
        if "bus_type" in dropped and not bus_type:
            continue
        if _count(db, origin, destination, relaxed_type, relaxed_budget) > 0:
            return {
                "dropped": dropped,
                "relaxed_slots": {"bus_type": relaxed_type, "budget": relaxed_budget},
            }
    return None


def compromise_text(
    dropped: list[str],
    budget: int | None,
    bus_type: str | None,
    cheapest_fare: int,
    cheapest_label: str,
) -> str:
    """Concrete ask naming the exact trade, never a bare 'no bus found'."""
    wanted = (bus_type or "bus").replace("_", " ")
    if dropped == ["budget"] and budget is not None:
        return (
            f"Nothing under Rs.{budget}, but {cheapest_label} at Rs.{cheapest_fare} fits "
            f"everything else — raise your budget by Rs.{cheapest_fare - budget}?"
        )
    if dropped == ["bus_type"]:
        return (
            f"No {wanted} on this route, but {cheapest_label} runs at Rs.{cheapest_fare} "
            f"— switch bus type?"
        )
    return (
        f"Nothing fits all of that, but {cheapest_label} starts at Rs.{cheapest_fare} "
        f"— shall I relax the budget and bus type?"
    )
