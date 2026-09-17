# ADR-004: Hybrid NLU — Gemini free tier for dialogue/slots + locally trained classifier

**Status:** Accepted

**Context:** This is a CSE-AIML major project: the report must show genuine AI/ML work, not only an API wrapper. A pure LLM approach is fastest but invites "where is the ML?"; a pure custom NLU (intent + slot-filling models) is brittle on free-form sentences like "book for my mom" and much more work.

**Decision:** Split the brain. **Gemini free tier** (structured-JSON output) handles dialogue and slot extraction — natural language understanding at the sentence level. **The team's own trained classifier** (embeddings + logistic head, see ADR-009) performs passenger-reference identification — the researched task — and is evaluated head-to-head against Gemini zero-shot on the same held-out data. Mistake detectors are deterministic logic (not ML).

**Alternatives considered:**
- Pure LLM API for everything — rejected: weak AIML story for the report.
- Custom NLU only (NLTK/spaCy intent+slots) — rejected: brittle, slower to build, worse accuracy on free-form text.

**Consequences:** One external dependency (Gemini, free tier) plus a fully local, free, explainable ML component with clean paper metrics. A fallback free OpenRouter model is configured for quota outages.
