import os

# Isolate every test run from the developer's seeded database: this MUST run
# before any app import reads Settings.
os.environ["DATABASE_URL"] = "sqlite://"
# WebAuthn ceremonies in tests run against the TestClient host and a soft
# authenticator bound to the same RP id.
os.environ["WEBAUTHN_RP_ID"] = "testserver"
os.environ["WEBAUTHN_ORIGIN"] = "https://testserver"
# Tests may create an admin user; production leaves this empty (fail closed).
os.environ["ADMIN_EMAILS"] = "admin@zerobusmail.com"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app import models  # noqa: E402, F401  (registers tables on Base.metadata)
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.payments import FakeGateway, set_gateway  # noqa: E402
set_gateway(FakeGateway())  # tests never touch money or network


@pytest.fixture
def test_mode_payments(monkeypatch):
    """Real gateway with test-mode keys; outbound Razorpay HTTP is stubbed.

    Suites that need an actually-paid booking (tickets, notifications) opt in
    here: demo orders are non-transactional by design and can never verify.
    """
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock

    from app.services import payments as payment_service

    monkeypatch.setattr(payment_service.settings, "razorpay_key_id", "rzp_test_conftest123")
    monkeypatch.setattr(payment_service.settings, "razorpay_key_secret", "private-test-secret")
    calls = {"count": 0}

    def respond(url, *, auth, json, timeout):
        calls["count"] += 1
        assert url == "https://api.razorpay.com/v1/orders"
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "id": f"order_stubtest{calls['count']}",
                "amount": json["amount"],
                "currency": "INR",
            },
        )

    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(post=Mock(side_effect=respond)))
    set_gateway(payment_service.RazorpayGateway())
    yield calls
    set_gateway(FakeGateway())


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
        db.commit()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session(db):
    return db


@pytest.fixture
def client(db):
    return TestClient(app)


@pytest.fixture
def client_with_db(client, db) -> tuple[TestClient, Session]:
    return client, db
