"""Deterministic synthetic bus inventory (ADR-005).

Timetables are hand-written template lists so seeding is fully reproducible.
Each template is a daily departure for the 30-day window.
Template tuple: (operator, bus_type, departure "HH:MM", duration_minutes, base_fare, total_seats)
"""

from datetime import time

from sqlalchemy.orm import Session

from app.models import Bus

ROUTES = [
    ("Bangalore", "Chennai"),
    ("Chennai", "Bangalore"),
    ("Bangalore", "Hyderabad"),
    ("Hyderabad", "Bangalore"),
    ("Bangalore", "Mysuru"),
    ("Mysuru", "Bangalore"),
    ("Bangalore", "Coimbatore"),
    ("Coimbatore", "Bangalore"),
    ("Bangalore", "Vijayawada"),
    ("Vijayawada", "Bangalore"),
    ("Bangalore", "Goa"),
    ("Goa", "Bangalore"),
    ("Bangalore", "Tirupati"),
    ("Tirupati", "Bangalore"),
    ("Bangalore", "Pondicherry"),
    ("Pondicherry", "Bangalore"),
]

PRIMARY_ROUTE = ("Bangalore", "Chennai")

_TIMETABLES = {
    ("Bangalore", "Chennai"): [
        ("SETC Express", "NON_AC_SEATER", "06:00", 420, 650, 50),
        ("KPN Travels", "AC_SEMI_SLEEPER", "07:30", 390, 850, 40),
        ("SRS Travels", "NON_AC_SEATER", "09:00", 420, 620, 50),
        ("Orange Tours", "AC_SEMI_SLEEPER", "11:30", 400, 900, 40),
        ("VRL Travels", "AC_SLEEPER", "14:00", 380, 1250, 36),
        ("KPN Travels", "AC_SLEEPER", "16:30", 390, 1300, 36),
        ("SRS Travels", "AC_SEMI_SLEEPER", "18:30", 400, 800, 44),
        ("Orange Tours", "NON_AC_SEATER", "20:00", 420, 700, 52),
        ("VRL Travels", "AC_SLEEPER", "22:30", 420, 1150, 36),
        ("KPN Travels", "AC_SLEEPER", "23:30", 435, 1350, 36),
    ],
    ("Chennai", "Bangalore"): [
        ("SETC Express", "NON_AC_SEATER", "05:30", 420, 640, 50),
        ("SRS Travels", "AC_SEMI_SLEEPER", "07:15", 400, 820, 44),
        ("KPN Travels", "NON_AC_SEATER", "09:30", 430, 660, 50),
        ("VRL Travels", "AC_SLEEPER", "13:00", 390, 1200, 36),
        ("Orange Tours", "AC_SEMI_SLEEPER", "15:30", 400, 880, 40),
        ("KPN Travels", "AC_SEMI_SLEEPER", "18:00", 395, 780, 44),
        ("SRS Travels", "AC_SLEEPER", "22:00", 430, 1100, 36),
        ("VRL Travels", "AC_SLEEPER", "23:15", 445, 1280, 36),
    ],
    ("Bangalore", "Hyderabad"): [
        ("SETC Express", "NON_AC_SEATER", "06:30", 510, 720, 50),
        ("Orange Tours", "AC_SEMI_SLEEPER", "08:00", 480, 950, 40),
        ("KPN Travels", "AC_SLEEPER", "10:30", 470, 1300, 36),
        ("SRS Travels", "NON_AC_SEATER", "13:30", 510, 680, 52),
        ("VRL Travels", "AC_SEMI_SLEEPER", "16:00", 490, 860, 44),
        ("Orange Tours", "AC_SLEEPER", "19:00", 475, 1240, 36),
        ("KPN Travels", "AC_SLEEPER", "22:00", 480, 1180, 36),
        ("SRS Travels", "AC_SLEEPER", "23:00", 495, 1090, 36),
    ],
    ("Hyderabad", "Bangalore"): [
        ("SETC Express", "NON_AC_SEATER", "06:00", 520, 700, 50),
        ("KPN Travels", "AC_SEMI_SLEEPER", "08:30", 490, 930, 40),
        ("VRL Travels", "AC_SLEEPER", "11:00", 480, 1290, 36),
        ("Orange Tours", "NON_AC_SEATER", "14:30", 510, 690, 52),
        ("SRS Travels", "AC_SEMI_SLEEPER", "17:00", 495, 840, 44),
        ("KPN Travels", "AC_SLEEPER", "20:30", 485, 1210, 36),
        ("Orange Tours", "AC_SLEEPER", "22:30", 500, 1120, 36),
        ("VRL Travels", "AC_SLEEPER", "23:45", 480, 1380, 36),
    ],
    ("Bangalore", "Mysuru"): [
        ("KPN Travels", "AC_SEMI_SLEEPER", "07:00", 210, 650, 40),
        ("SETC Express", "NON_AC_SEATER", "09:30", 220, 600, 50),
        ("SRS Travels", "AC_SEMI_SLEEPER", "14:00", 210, 680, 44),
        ("VRL Travels", "AC_SLEEPER", "17:30", 215, 750, 36),
    ],
    ("Mysuru", "Bangalore"): [
        ("SETC Express", "NON_AC_SEATER", "06:30", 220, 600, 50),
        ("KPN Travels", "AC_SEMI_SLEEPER", "10:00", 210, 660, 40),
        ("Orange Tours", "AC_SEMI_SLEEPER", "15:30", 215, 700, 44),
        ("SRS Travels", "AC_SLEEPER", "19:00", 210, 740, 36),
    ],
    ("Bangalore", "Coimbatore"): [
        ("SETC Express", "NON_AC_SEATER", "06:30", 460, 700, 50),
        ("KPN Travels", "AC_SEMI_SLEEPER", "09:00", 450, 950, 40),
        ("SRS Travels", "AC_SLEEPER", "15:00", 445, 1150, 36),
        ("VRL Travels", "AC_SLEEPER", "22:30", 460, 1200, 36),
    ],
    ("Coimbatore", "Bangalore"): [
        ("SETC Express", "NON_AC_SEATER", "06:00", 460, 710, 50),
        ("Orange Tours", "AC_SEMI_SLEEPER", "10:30", 455, 940, 40),
        ("KPN Travels", "AC_SLEEPER", "14:30", 450, 1140, 36),
        ("SRS Travels", "AC_SLEEPER", "22:00", 465, 1190, 36),
    ],
    ("Bangalore", "Vijayawada"): [
        ("SETC Express", "NON_AC_SEATER", "07:00", 730, 900, 50),
        ("Orange Tours", "AC_SEMI_SLEEPER", "12:00", 720, 1050, 40),
        ("KPN Travels", "AC_SLEEPER", "18:00", 710, 1300, 36),
        ("VRL Travels", "AC_SLEEPER", "21:30", 725, 1400, 36),
    ],
    ("Vijayawada", "Bangalore"): [
        ("SETC Express", "NON_AC_SEATER", "06:30", 730, 910, 50),
        ("SRS Travels", "AC_SEMI_SLEEPER", "11:00", 725, 1040, 40),
        ("Orange Tours", "AC_SLEEPER", "17:30", 715, 1290, 36),
        ("KPN Travels", "AC_SLEEPER", "21:00", 730, 1390, 36),
    ],
    ("Bangalore", "Goa"): [
        ("VRL Travels", "AC_SLEEPER", "18:00", 710, 1350, 36),
        ("SRS Travels", "AC_SLEEPER", "19:30", 720, 1300, 36),
        ("Orange Tours", "AC_SEMI_SLEEPER", "20:30", 730, 1050, 40),
        ("KPN Travels", "AC_SLEEPER", "22:00", 715, 1400, 36),
    ],
    ("Goa", "Bangalore"): [
        ("VRL Travels", "AC_SLEEPER", "17:30", 720, 1350, 36),
        ("Orange Tours", "AC_SEMI_SLEEPER", "19:00", 730, 1040, 40),
        ("SRS Travels", "AC_SLEEPER", "20:00", 715, 1290, 36),
        ("SETC Express", "NON_AC_SEATER", "21:30", 740, 1000, 50),
    ],
    ("Bangalore", "Tirupati"): [
        ("SETC Express", "NON_AC_SEATER", "06:00", 240, 600, 50),
        ("KPN Travels", "AC_SEMI_SLEEPER", "08:30", 235, 720, 40),
        ("SRS Travels", "AC_SEMI_SLEEPER", "13:00", 240, 700, 44),
        ("Orange Tours", "NON_AC_SEATER", "16:30", 245, 640, 52),
    ],
    ("Tirupati", "Bangalore"): [
        ("SETC Express", "NON_AC_SEATER", "05:30", 245, 600, 50),
        ("Orange Tours", "AC_SEMI_SLEEPER", "09:00", 240, 710, 40),
        ("KPN Travels", "AC_SEMI_SLEEPER", "14:30", 235, 730, 44),
        ("SRS Travels", "NON_AC_SEATER", "18:00", 240, 650, 52),
    ],
    ("Bangalore", "Pondicherry"): [
        ("SETC Express", "NON_AC_SEATER", "07:30", 470, 750, 50),
        ("KPN Travels", "AC_SEMI_SLEEPER", "10:00", 460, 950, 40),
        ("SRS Travels", "AC_SLEEPER", "15:30", 455, 1100, 36),
        ("VRL Travels", "AC_SLEEPER", "22:00", 470, 1080, 36),
    ],
    ("Pondicherry", "Bangalore"): [
        ("SETC Express", "NON_AC_SEATER", "06:00", 470, 760, 50),
        ("Orange Tours", "AC_SEMI_SLEEPER", "09:30", 465, 940, 40),
        ("KPN Travels", "AC_SLEEPER", "14:00", 460, 1090, 36),
        ("VRL Travels", "AC_SLEEPER", "21:30", 475, 1070, 36),
    ],
}


def _parse_hh_mm(value) -> time:
    if isinstance(value, time):
        return value
    hours, minutes = str(value).split(":")
    return time(int(hours), int(minutes))


def _build_bus(operator, bus_type, departure, duration_minutes, base_fare, total_seats) -> Bus:
    dep = _parse_hh_mm(departure)
    total = dep.hour * 60 + dep.minute + duration_minutes
    arrival_day_offset, arr_minutes = divmod(total, 24 * 60)
    arrival = time(arr_minutes // 60 % 24, arr_minutes % 60)
    return Bus(
        operator=operator,
        bus_type=bus_type,
        departure_time=dep,
        arrival_time=arrival,
        arrival_day_offset=arrival_day_offset,
        duration_minutes=duration_minutes,
        base_fare=base_fare,
        total_seats=total_seats,
    )


def seed_buses(session: Session) -> None:
    # Additive: fresh databases get all routes; live databases missing newer
    # corridors get only those (existing bookings keep their bus rows).
    existing = {
        (origin, destination)
        for origin, destination in session.query(Bus.origin, Bus.destination).distinct()
    }
    for (origin, destination), templates in _TIMETABLES.items():
        if (origin, destination) in existing:
            continue
        for operator, bus_type, departure, duration, fare, seats in templates:
            bus = _build_bus(operator, bus_type, departure, duration, fare, seats)
            bus.origin = origin
            bus.destination = destination
            session.add(bus)
    session.commit()
