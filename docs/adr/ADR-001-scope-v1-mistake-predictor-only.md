# ADR-001: v1 scope — Mistake Predictor as the only add-on; deferred items map to Phase 2 Chapter 7

**Status:** Accepted

**Context:** The Phase 2 report promises a broad system (booking, QR, predictive analytics, tracking, crowd detection, dashboard, payments, notifications). The team also wants three candidate AI add-ons (Requirement Negotiator, Mistake Predictor, Undo/Versions). With 4 members and one semester, doing everything deeply is not credible; a diluted version of everything would weaken both the demo and the paper.

**Decision:** Ship v1 as: every Phase 2 promise that needs no special hardware + the zero-form/self-vs-other research core + the **Mistake Predictor only** (four detectors). Deferred: real GPS (simulated instead), CCTV crowd detection (seat-occupancy proxy instead), NFC/RFID, SMS, facial recognition, mobile app, multilingual, offline validation, route optimization, Negotiator, Undo.

**Alternatives considered:**
- All three add-ons — rejected: three half-finished features, no clear research focus.
- Mistake Predictor + Negotiator — rejected: two AI behaviours to design *and* evaluate, ~40% more work.
- Mistake Predictor + Undo — rejected: versioning is neat but hard to measure in a user study.

**Consequences:** The Mistake Predictor gets depth (four detector types, each an experiment section in the paper). Every deferred item can be justified to examiners by pointing at the Phase 2 report's own Chapter 7 "Planned Enhancements" list.
