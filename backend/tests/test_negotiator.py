"""Requirement Negotiator — RED: compromise suggestions on empty results."""

from datetime import date, timedelta

TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def test_exact_match_needs_no_negotiation(client, session):
    from app.seed.buses import seed_buses
    from app.services import negotiator

    seed_buses(session)
    travel = date.today() + timedelta(days=1)
    assert negotiator.relax_search(session, "Bangalore", "Chennai", travel) is None


def test_impossible_route_returns_none(client, session):
    from app.seed.buses import seed_buses
    from app.services import negotiator

    seed_buses(session)
    travel = date.today() + timedelta(days=1)
    assert negotiator.relax_search(session, "Nowhere", "Noland", travel, budget=700) is None


def test_tight_budget_suggests_raising_it(client, session):
    from app.seed.buses import seed_buses
    from app.services import negotiator

    seed_buses(session)
    travel = date.today() + timedelta(days=1)
    # Cheapest AC sleeper BLR->Chennai is Rs.1100; Rs.700 matches nothing.
    result = negotiator.relax_search(
        session, "Bangalore", "Chennai", travel, bus_type="AC_SLEEPER", budget=700
    )
    assert result is not None
    assert result["dropped"] == ["budget"]
    assert result["relaxed_slots"] == {"bus_type": "AC_SLEEPER", "budget": None}
    # The relaxed slots must yield a concrete alternative above Rs.700.
    from app.models import Bus

    cheapest = (
        session.query(Bus)
        .filter(Bus.origin == "Bangalore", Bus.destination == "Chennai", Bus.bus_type == "AC_SLEEPER")
        .order_by(Bus.base_fare)
        .first()
    )
    assert cheapest is not None and cheapest.base_fare > 700


def test_relaxation_order_budget_before_type(client, session):
    from app.seed.buses import seed_buses
    from app.services import negotiator

    seed_buses(session)
    travel = date.today() + timedelta(days=1)
    result = negotiator.relax_search(
        session, "Bangalore", "Chennai", travel, bus_type="AC_SLEEPER", budget=100
    )
    # Dropping only the budget already yields AC sleepers, so the bus type
    # the traveller asked for is preserved.
    assert result is not None and result["dropped"] == ["budget"]


def test_chat_offers_negotiation_instead_of_empty_list(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    from tests.test_booking import _headers

    headers = _headers(client)
    reply = client.post(
        "/api/booking/chat",
        json={
            "session_id": "negotiate-1",
            "message": "AC sleeper from Bangalore to Chennai tomorrow below 700 for me",
        },
        headers=headers,
    ).json()
    assert reply.get("negotiation"), "expected a compromise offer, not an empty list"
    assert reply["negotiation"]["dropped"] == ["budget"]
    assert reply.get("buses"), "suggested buses keep the booking flow going"
    assert "700" in reply["assistant_text"] or "budget" in reply["assistant_text"].lower()


def test_chat_unknown_route_names_served_corridors(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    from tests.test_booking import _headers

    headers = _headers(client)
    reply = client.post(
        "/api/booking/chat",
        json={
            "session_id": "unknown-route-1",
            "message": "Chennai to Hyderabad tomorrow for me",
        },
        headers=headers,
    ).json()
    assert reply.get("buses") == []
    assert reply["state"] == "NEEDS_INFO"
    assert "No direct buses" in reply["assistant_text"]
    assert "Bangalore" in reply["assistant_text"]
    assert len(reply.get("served_routes", [])) == 8
    # Route slots reset so the next message starts clean.
    assert "origin" not in reply["slots"]
    assert "destination" not in reply["slots"]
