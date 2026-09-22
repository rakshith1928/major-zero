"""OpenRouter slot extraction with stub fallback (TDD RED)."""

from app.services import extractor


def test_openrouter_extractor_parses_valid_json():
    def fake_post(message, session_slots):
        return {
            "origin": "Bangalore",
            "destination": "Chennai",
            "travel_date": "2026-09-20",
        }

    ex = extractor.OpenRouterSlotExtractor(api_key="test-key", http_post=fake_post)
    slots = ex.extract("anything at all", {})
    assert slots["origin"] == "Bangalore"
    assert slots["destination"] == "Chennai"


def test_openrouter_extractor_falls_back_to_stub_on_error():
    def boom(message, session_slots):
        raise RuntimeError("network down")

    ex = extractor.OpenRouterSlotExtractor(api_key="test-key", http_post=boom)
    slots = ex.extract("bangalore to chennai", {})
    # stub fallback must still catch the origin (fixed regex)
    assert slots.get("origin") == "Bangalore"
    assert slots.get("destination") == "Chennai"


def test_openrouter_extractor_without_key_uses_stub_only():
    ex = extractor.OpenRouterSlotExtractor(api_key="", http_post=None)
    slots = ex.extract("bangalore to chennai", {})
    assert slots.get("origin") == "Bangalore"


def test_openrouter_default_model_is_free_router():
    ex = extractor.OpenRouterSlotExtractor(api_key="test-key")
    assert ex.model == "openrouter/free"


def test_openrouter_default_timeout_is_chat_friendly():
    # A chat turn must never hang on the LLM: worst case it waits a few
    # seconds, then the stub answers.
    ex = extractor.OpenRouterSlotExtractor(api_key="test-key")
    assert ex.timeout <= 5
