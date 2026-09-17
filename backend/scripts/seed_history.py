"""Seed the six-month synthetic booking history into the configured database.

Usage (from backend/):  ../.venv/Scripts/python scripts/seed_history.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models  # noqa: E402, F401  (registers tables on Base.metadata)
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Booking  # noqa: E402
from app.seed.buses import seed_buses  # noqa: E402
from app.seed.history import seed_history  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_buses(session)
        seed_history(session)
        print(f"synthetic bookings: {session.query(Booking).filter(Booking.is_synthetic.is_(True)).count()}")


if __name__ == "__main__":
    main()
