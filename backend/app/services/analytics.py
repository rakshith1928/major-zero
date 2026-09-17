"""T09 — demand prediction, crowd levels, fare indicator.

The predictor is a lightweight, explainable model over the synthetic history:
per (route, weekday, departure-hour bucket) occupancy rates. A scikit-learn
RandomForest version trains in research/ (notebook) for the paper; the API
uses these transparent rates so behavior is deterministic and testable.
"""

from collections import defaultdict
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Booking, Bus


def occupancy_rates(db: Session) -> dict:
    """Mean occupancy keyed by (origin, destination, weekday, dep_hour)."""
    totals: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    rows = (
        db.query(Booking, Bus)
        .join(Bus, Booking.bus_id == Bus.id)
        .filter(Booking.is_synthetic.is_(True))
        .all()
    )
    per_bus_day: dict[tuple, int] = defaultdict(int)
    for booking, _bus in rows:
        per_bus_day[(booking.bus_id, booking.travel_date)] += 1
    buses = {b.id: b for b in db.query(Bus).all()}
    for (bus_id, travel_date), count in per_bus_day.items():
        bus = buses[bus_id]
        key = (
            bus.origin,
            bus.destination,
            travel_date.weekday(),
            bus.departure_time.hour,
        )
        acc = totals[key]
        acc[0] += count / bus.total_seats
        acc[1] += 1
    return {key: acc[0] / acc[1] for key, acc in totals.items()}


def predict_occupancy(db: Session, origin: str, destination: str, travel: date, dep_hour: int) -> float:
    rates = occupancy_rates(db)
    key = (origin, destination, travel.weekday(), dep_hour)
    if key in rates:
        return rates[key]
    # Back off: same route any weekday/hour, else global mean, else 0.4 prior.
    same_route = [v for k, v in rates.items() if k[0] == origin and k[1] == destination]
    if same_route:
        return sum(same_route) / len(same_route)
    if rates:
        return sum(rates.values()) / len(rates)
    return 0.4


def demand_curve(db: Session, origin: str, destination: str, travel: date) -> list[dict]:
    buses = (
        db.query(Bus)
        .filter(Bus.origin == origin, Bus.destination == destination)
        .order_by(Bus.departure_time)
        .all()
    )
    points = [
        {
            "bus_id": b.id,
            "departure": b.departure_time.strftime("%H:%M"),
            "predicted_occupancy": round(
                predict_occupancy(db, origin, destination, travel, b.departure_time.hour), 3
            ),
        }
        for b in buses
    ]
    if points:
        ordered = sorted(p["predicted_occupancy"] for p in points)
        peak_index = max(0, len(ordered) - max(1, len(ordered) // 3) - 1)
        peak_threshold = ordered[peak_index]
        for point in points:
            point["is_peak"] = point["predicted_occupancy"] >= peak_threshold
    return points


def fare_indicator(occupancy: float) -> str:
    if occupancy >= 0.75:
        return "HIGH"
    if occupancy <= 0.35:
        return "LOW"
    return "NORMAL"


def crowd_level(db: Session, bus_id: int, travel: date) -> float:
    bus = db.get(Bus, bus_id)
    booked = (
        db.query(func.count(Booking.id))
        .filter(Booking.bus_id == bus_id, Booking.travel_date == travel)
        .filter(Booking.status.in_(["PENDING_PAYMENT", "PAID"]))
        .scalar()
    ) or 0
    return round(min(1.0, booked / bus.total_seats), 3)
