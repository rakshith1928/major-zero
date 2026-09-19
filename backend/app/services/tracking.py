"""T10 — simulated GPS (ADR-013).

Each route is a straight-line corridor between two city coordinates with a
midpoint stop. A bus's position is a deterministic function of "now":
progress = clamp((now - departure) / duration). No worker, no persistence —
positions are pure computation, hence cheap to poll and trivially testable.
The API always reports simulated=True (disclosure requirement).
"""

from datetime import date, datetime, time

# City coordinates (approx): Bangalore, Chennai, Hyderabad midpoint stops.
STOPS = {
    "Bangalore": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Vellore": (12.9165, 79.1325),  # Bangalore–Chennai midpoint
    "Kurnool": (15.8281, 78.0373),  # Bangalore–Hyderabad midpoint
}

_MIDPOINT = {
    ("Bangalore", "Chennai"): "Vellore",
    ("Chennai", "Bangalore"): "Vellore",
    ("Bangalore", "Hyderabad"): "Kurnool",
    ("Hyderabad", "Bangalore"): "Kurnool",
}

# Trip Guardian demo: per-bus delay overrides (minutes) held in memory.
# Single-worker deployments only; cleared on restart. The public API keeps
# reporting simulated=True, and overrides exist solely to stage delay
# scenarios for demos and tests — never real GPS data.
_DELAY_OVERRIDES: dict[int, int] = {}


def set_delay(bus_id: int, minutes: int) -> None:
    """Stage a simulated delay for one bus. Non-positive values are ignored."""
    if minutes > 0:
        _DELAY_OVERRIDES[int(bus_id)] = int(minutes)


def clear_delay(bus_id: int) -> None:
    _DELAY_OVERRIDES.pop(int(bus_id), None)


def delay_for(bus_id: int) -> int:
    return _DELAY_OVERRIDES.get(int(bus_id), 0)


def corridor(origin: str, destination: str) -> list[tuple[str, tuple[float, float]]]:
    mid = _MIDPOINT.get((origin, destination))
    points = [(origin, STOPS[origin])]
    if mid:
        points.append((mid, STOPS[mid]))
    points.append((destination, STOPS[destination]))
    return points


def _lerp(a: tuple[float, float], b: tuple[float, float], t: float):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def position_for(bus, travel: date, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    dep = datetime.combine(travel, bus.departure_time)
    total = bus.duration_minutes * 60
    elapsed = (now - dep).total_seconds()
    progress = max(0.0, min(1.0, elapsed / total if total else 1.0))
    points = corridor(bus.origin, bus.destination)
    # Piecewise along corridor stops.
    segments = len(points) - 1
    scaled = progress * segments
    idx = min(int(scaled), segments - 1)
    frac = scaled - idx
    lat, lon = _lerp(points[idx][1], points[idx + 1][1], frac)
    remaining_minutes = max(0, int((total - elapsed) // 60)) + delay_for(bus.id)
    return {
        "bus_id": bus.id,
        "lat": round(lat, 4),
        "lon": round(lon, 4),
        "progress": round(progress, 3),
        "status": "COMPLETED" if progress >= 1.0 else ("EN_ROUTE" if progress > 0 else "SCHEDULED"),
        "remaining_minutes": remaining_minutes,
        "corridor": [name for name, _ in points],
    }


def eta_to_stop(bus, travel: date, stop: str, now: datetime | None = None) -> dict:
    pos = position_for(bus, travel, now)
    points = corridor(bus.origin, bus.destination)
    names = [name for name, _ in points]
    if stop not in names:
        stop = bus.origin
    stop_fraction = names.index(stop) / max(1, len(names) - 1)
    remaining_fraction = max(0.0, stop_fraction - pos["progress"])
    eta_minutes = int(remaining_fraction * bus.duration_minutes) + delay_for(bus.id)
    return {
        "bus_id": bus.id,
        "stop": stop,
        "eta_minutes": eta_minutes,
        "status": pos["status"],
        "simulated": True,
    }
