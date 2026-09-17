from datetime import date

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Booking, Bus, User
from app.seed.buses import seed_buses
from app.seed.history import HISTORY_DAYS, seed_history

TODAY = date.today()


@pytest.fixture(scope="module")
def seeded_session():
    """History tests are read-only: one shared in-memory DB for the module."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed_buses(s)
    seed_history(s)
    yield s
    s.close()
    engine.dispose()


def test_history_covers_six_past_months(seeded_session):
    bookings = (
        seeded_session.query(Booking).filter(Booking.is_synthetic.is_(True)).all()
    )
    assert bookings, "no synthetic history seeded"
    oldest = min(b.travel_date for b in bookings)
    assert (TODAY - oldest).days >= HISTORY_DAYS - 7
    assert all(b.travel_date < TODAY for b in bookings)


def test_synthetic_bookings_belong_to_synthetic_users_and_are_paid(seeded_session):
    synthetic = (
        seeded_session.query(Booking).filter(Booking.is_synthetic.is_(True)).all()
    )
    assert synthetic
    synthetic_user_ids = {
        u.id
        for u in seeded_session.query(User).filter(User.is_synthetic.is_(True)).all()
    }
    assert all(b.user_id in synthetic_user_ids for b in synthetic)
    assert all(b.status == "PAID" for b in synthetic)


def test_weekend_demand_exceeds_midweek_demand(seeded_session):
    bookings = (
        seeded_session.query(Booking).filter(Booking.is_synthetic.is_(True)).all()
    )
    weekend = [b for b in bookings if b.travel_date.weekday() >= 5]
    midweek = [b for b in bookings if 1 <= b.travel_date.weekday() <= 3]
    assert weekend and midweek
    assert len(weekend) / 2 / (HISTORY_DAYS / 7) > len(midweek) / 3 / (HISTORY_DAYS / 7)


def test_bookings_never_exceed_bus_capacity(seeded_session):
    counts = (
        seeded_session.query(
            Booking.bus_id, Booking.travel_date, func.count(Booking.id)
        )
        .filter(Booking.is_synthetic.is_(True))
        .group_by(Booking.bus_id, Booking.travel_date)
        .all()
    )
    capacities = {b.id: b.total_seats for b in seeded_session.query(Bus).all()}
    assert counts
    assert all(n <= capacities[bus_id] for bus_id, _d, n in counts)


def test_history_seeding_is_deterministic(session):
    def fresh_rows():
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        s = sessionmaker(bind=engine, expire_on_commit=False)()
        seed_buses(s)
        seed_history(s)
        rows = sorted(
            (b.user_id, b.bus_id, b.travel_date.isoformat(), b.fare, b.status)
            for b in s.query(Booking).all()
        )
        s.close()
        engine.dispose()
        return rows

    assert fresh_rows() == fresh_rows()
