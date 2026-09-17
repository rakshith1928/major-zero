from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Bus
from app.seed.buses import PRIMARY_ROUTE, ROUTES, seed_buses


def test_seeding_produces_buses_for_all_configured_routes(session):
    seed_buses(session)
    pairs = {(b.origin, b.destination) for b in session.query(Bus).all()}
    assert pairs == set(ROUTES)


def test_primary_route_has_overnight_bus_arriving_early_morning(session):
    seed_buses(session)
    origin, destination = PRIMARY_ROUTE
    overnight = (
        session.query(Bus)
        .filter_by(origin=origin, destination=destination, arrival_day_offset=1)
        .all()
    )
    assert overnight, "the study scenarios need an overnight bus on the primary route"
    assert any(5 <= b.arrival_time.hour <= 8 for b in overnight)


def test_all_fares_within_reported_band(session):
    seed_buses(session)
    fares = [b.base_fare for b in session.query(Bus).all()]
    assert fares and all(600 <= f <= 1400 for f in fares)


def test_all_three_reported_bus_classes_present(session):
    seed_buses(session)
    types = {b.bus_type for b in session.query(Bus).all()}
    assert {"AC_SLEEPER", "AC_SEMI_SLEEPER", "NON_AC_SEATER"} <= types


def test_seeding_is_deterministic(session):
    def fresh_rows():
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        s = sessionmaker(bind=engine, expire_on_commit=False)()
        seed_buses(s)
        rows = sorted(
            (
                b.origin,
                b.destination,
                b.operator,
                b.bus_type,
                b.departure_time.isoformat(),
                b.arrival_time.isoformat(),
                b.arrival_day_offset,
                b.base_fare,
                b.total_seats,
            )
            for b in s.query(Bus).all()
        )
        s.close()
        engine.dispose()
        return rows

    assert fresh_rows() == fresh_rows()
