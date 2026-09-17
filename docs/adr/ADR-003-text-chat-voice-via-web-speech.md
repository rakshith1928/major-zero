# ADR-003: Text chat as the primary input; voice via free browser Web Speech API

**Status:** Accepted

**Context:** The Phase 2 report mentions chatbot + voice-based assistance (and also lists voice as a future enhancement). Voice-first would make accuracy metrics ambiguous — is an error the speech recognizer's or the AI's? — and paid STT APIs cost money per request.

**Decision:** The conversation is text chat. Voice input is added through the browser's built-in Web Speech API (Chrome/Edge, free, no key) feeding the identical text pipeline, satisfying the report's voice checkbox without changing the AI or the metrics. No TTS voice replies in v1.

**Alternatives considered:**
- Voice-first with Whisper/Google STT — rejected: cost, transcription noise polluting metrics, extra moving part.
- No voice at all in v1 — rejected: cheap to add via Web Speech API and the report's abstract promises it.

**Consequences:** Deterministic evaluation of AI accuracy; voice is a demo layer. Browsers other than Chrome/Edge fall back to text-only, which must be noted in the demo script.
