"""Booking Undo — RED: version stack restores previous slot choices."""

from datetime import date, timedelta


def _chat(client, headers, session_id, message):
    return client.post(
        "/api/booking/chat",
        json={"session_id": session_id, "message": message},
        headers=headers,
    ).json()


def test_undo_restores_previous_bus_type(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    from tests.test_booking import _headers

    headers = _headers(client)
    first = _chat(client, headers, "undo-1", "AC sleeper from Bangalore to Chennai tomorrow for me")
    assert first["slots"].get("bus_type") == "AC_SLEEPER"
    second = _chat(client, headers, "undo-1", "Actually make it non-AC")
    assert second["slots"].get("bus_type") == "NON_AC_SEATER"
    undone = _chat(client, headers, "undo-1", "Undo my last change")
    assert undone["slots"].get("bus_type") == "AC_SLEEPER"
    assert undone["slots"].get("origin") == "Bangalore"
    assert "back" in undone["assistant_text"].lower()


def test_undo_with_empty_history_is_graceful(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    from tests.test_booking import _headers

    headers = _headers(client)
    reply = _chat(client, headers, "undo-fresh", "undo that")
    assert reply["state"] == "NEEDS_INFO"
    assert "nothing to undo" in reply["assistant_text"].lower()


def test_second_undo_walks_further_back(client, session):
    from app.seed.buses import seed_buses

    seed_buses(session)
    from tests.test_booking import _headers

    headers = _headers(client)
    _chat(client, headers, "undo-2", "AC sleeper from Bangalore to Chennai tomorrow for me")
    _chat(client, headers, "undo-2", "Actually make it non-AC")
    _chat(client, headers, "undo-2", "undo my last change")
    twice = _chat(client, headers, "undo-2", "undo again")
    # Two undos return to the very first understood state (bus type unset
    # before AC was ever mentioned) or report nothing left to undo.
    assert (
        twice["slots"].get("bus_type") in (None, "AC_SLEEPER")
        or "nothing to undo" in twice["assistant_text"].lower()
    )
