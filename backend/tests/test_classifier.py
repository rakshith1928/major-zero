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


def test_local_snapshot_resolution_prefers_cache(tmp_path):
    from app.services import passenger_ref as pr

    snap = tmp_path / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    (snap / "config.json").write_text("{}")
    found = pr._resolve_local_snapshot(str(tmp_path), "sentence-transformers/all-MiniLM-L6-v2")
    assert found is not None and found.endswith("abc123")


def test_local_snapshot_resolution_misses_cleanly(tmp_path):
    from app.services import passenger_ref as pr

    assert pr._resolve_local_snapshot(str(tmp_path), "sentence-transformers/all-MiniLM-L6-v2") is None


def test_trained_ref_uses_local_snapshot_first(tmp_path, monkeypatch):
    import pickle

    from app.services import passenger_ref as pr

    snap = tmp_path / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    (snap / "config.json").write_text("{}")
    pkl = tmp_path / "model.pkl"
    pkl.write_bytes(pickle.dumps({"kind": "minilm", "model_name": "sentence-transformers/all-MiniLM-L6-v2", "classifier": None, "labels": ["self"]}))
    seen = {}
    monkeypatch.setenv("HF_HOME", str(tmp_path))

    class FakeST:
        def __init__(self, name):
            seen["name"] = name

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeST)
    ref = pr.TrainedPassengerRef(str(pkl))
    assert seen["name"].endswith("abc123"), "must load from local snapshot, not hub"
    _reset()
    set_classifier(lambda text: "other")
    assert classify_passenger_ref("anything at all") == "other"
    _reset()
    assert classify_passenger_ref("Book a ticket for me") == "self"
