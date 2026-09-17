"""T04 — passenger-ref classifier contract through its public seam.

The rule-based `KeywordPassengerRef` is the always-available fallback; the
trained embeddings model (research/) overrides it via `set_classifier()`.
These tests pin the routing behavior the chat flow needs.
"""

from app.services.passenger_ref import (
    KeywordPassengerRef,
    classify_passenger_ref,
    set_classifier,
)


def _reset():
    set_classifier(KeywordPassengerRef())


def test_self_utterances_route_to_self():
    _reset()
    for text in [
        "Book a ticket for me",
        "I need one seat for myself",
        "book my ticket for tomorrow",
    ]:
        assert classify_passenger_ref(text) == "self", text


def test_other_utterances_route_to_other():
    _reset()
    for text in [
        "Book a ticket for my mother",
        "I need a seat for my dad",
        "book for my wife and me",
    ]:
        assert classify_passenger_ref(text) == "other", text


def test_plural_or_bare_counts_route_to_ambiguous():
    _reset()
    for text in [
        "Book two tickets",
        "I need 3 seats",
        "book a bus to Chennai",
    ]:
        assert classify_passenger_ref(text) == "ambiguous", text


def test_custom_classifier_overrides_default():
    _reset()
    set_classifier(lambda text: "other")
    assert classify_passenger_ref("anything at all") == "other"
    _reset()
    assert classify_passenger_ref("Book a ticket for me") == "self"
