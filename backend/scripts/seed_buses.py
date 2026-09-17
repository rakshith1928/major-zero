"""Seed the daily bus timetable into the configured database.

Usage (from backend/):  ../.venv/Scripts/python scripts/seed_buses.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models  # noqa: E402, F401  (registers tables on Base.metadata)
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Bus  # noqa: E402
from app.seed.buses import seed_buses  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_buses(session)
        print(f"buses seeded: {session.query(Bus).count()}")


if __name__ == "__main__":
    main()
