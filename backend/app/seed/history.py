"""Deterministic six-month synthetic booking history (ADR-005).

Generates past bookings with a weekend/seasonal demand pattern so the demand
model (T09) has something realistic to learn from.
"""

import random
from datetime import date, datetime, timedelta

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.models import Booking, Bus, PassengerProfile, User

HISTORY_DAYS = 180
SYNTHETIC_USERS = 60
RNG_SEED = 42

_WEEKEND_BOOST = {4: 0.22, 5: 0.28, 6: 0.25}  # Friday, Saturday, Sunday departures


def _demand_rate(rng: random.Random, travel_date: date) -> float:
    weekend = _WEEKEND_BOOST.get(travel_date.weekday(), 0.0)
    seasonal = 0.06 * (1 + (travel_date.day % 15) / 14)  # deterministic monthly wave
    noise = rng.uniform(-0.15, 0.15)
    rate = 0.40 + weekend + seasonal + noise
    return max(0.05, min(0.95, rate))


def seed_history(session: Session) -> None:
    if session.query(User).filter(User.is_synthetic.is_(True)).count():
        return

    rng = random.Random(RNG_SEED)
    users = [
        User(email=f"traveller{n}@zerobusmail.com", is_synthetic=True)
        for n in range(1, SYNTHETIC_USERS + 1)
    ]
    session.add_all(users)
    session.flush()

    for user in users:
        session.add(
            PassengerProfile(
                owner_user_id=user.id,
                is_self=True,
                label="Self",
                data_encrypted="synthetic",
                consent_given=True,
            )
        )
    session.flush()

    buses = session.query(Bus).all()
    today = date.today()
    rows: list[dict] = []
    for bus in buses:
        for offset in range(HISTORY_DAYS, 0, -1):
            travel_date = today - timedelta(days=offset)
            rate = _demand_rate(rng, travel_date)
            seats_taken = int(rate * bus.total_seats)
            for _ in range(seats_taken):
                user = rng.choice(users)
                rows.append(
                    {
                        "booking_ref": f"S{len(rows):08d}",
                        "user_id": user.id,
                        "bus_id": bus.id,
                        "travel_date": travel_date,
                        "passenger_snapshot_encrypted": "synthetic",
                        "boarding_point": bus.origin,
                        "fare": bus.base_fare,
                        "deadline_time": None,
                        "status": "PAID",
                        "is_synthetic": True,
                        "created_at": datetime.combine(
                            travel_date - timedelta(days=2), datetime.min.time()
                        ),
                    }
                )
    session.execute(insert(Booking), rows)
    session.commit()
