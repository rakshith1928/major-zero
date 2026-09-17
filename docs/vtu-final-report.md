# VTU Final Report Content — ZeroBus (Phase 3 additions to the Phase 2 report)

Follows the Phase 2 report's chapter structure. New AI modules are presented
as Phase 3 additions. Mandatory disclosures: synthetic inventory (ADR-005),
simulated GPS (ADR-013), Razorpay test mode (ADR-007), RedBus cutoff protocol
(ADR-008).

## 1. Introduction
Phase 2 delivered smart ticketing with predictive analytics. Phase 3 adds the
research layer: fingerprint authentication, zero-form booking, AI
self-vs-other passenger identification, and the Pre-Booking Mistake Predictor.
Problem: repeated form-filling and silent booking mistakes. Objectives,
scope, and disclosures as in `docs/spec.md`.

## 2. Literature Review
Conversational booking assistants; WebAuthn/passkey adoption studies;
passenger-demand forecasting (RandomForest, time-series); checkout error
prevention; QR ticketing and fraud; usability (SUS) and privacy-perception
measurement in transport apps.

## 3. Research Methodology
Hybrid NLU (Gemini slot extraction + local classifier); dataset construction
(templates + paraphrase + classmate collection); stratified evaluation with
LLM head-to-head; four pure-function mistake detectors with logged outcomes;
within-subject counterbalanced study vs RedBus (payment-screen cutoff),
familiarity covariate, paired Wilcoxon analysis.

## 4. System Design & Architecture
Layers: React frontend (chat, wallet, verify, map, dashboard, profile) →
FastAPI routers (auth, passkeys, booking, passengers, warnings, payments,
tickets, analytics, tracking, admin, notifications, metrics) → services
(vault, extractor, passenger_ref, detectors, payments, tickets, analytics,
tracking, notifications) → SQLAlchemy models (SQLite dev / MySQL demo).
External: Gemini (slots), Razorpay test checkout, SMTP email, OSM tiles.

## 5. Implementation
T01 seeded inventory (34 buses, 4 routes) + 6-month synthetic history;
T02 WebAuthn ceremony (fido2) + argon2 fallback + Fernet vault; T03 chat
state machine + stub extractor seam; T04 MiniLM + logistic head (93.9%
accuracy, macro F1 0.937, n=114) + Gemini zero-shot protocol; T05 capture +
opt-in memory + view/delete; T06 four detectors + warnings API + safer
alternatives; T08/T07 payments + signed single-use QR; T09 demand API (MAE
0.077) + crowd/fare chips; T10 simulated-GPS map (SIMULATION badge); T11
admin overview; T12 notifications; T13 metrics + study pack.

## 6. Results & Analysis
Classifier metrics, demand MAE + importances, backend suite green, frontend
`tsc` + build green, all figures reproducible from `research/results/`.
Study results section fills in after data collection via
`research/analysis_template.py`.

## 7. Planned Enhancements & Conclusion
Negotiator, Undo/versions, real GPS, CCTV crowding, SMS, facial recognition,
mobile apps, multilingual, offline validation — as listed in Phase 2
Chapter 7. Conclusion: context-aware identity plus pre-payment warnings make
booking faster, safer, and measurably more private-feeling.

## 8. References
Phase 2 references carry over, plus: WebAuthn/FIDO2 specs, MiniLM paper,
Gemini API docs, Razorpay test-mode docs, SUS (Brooke 1996), Leaflet/OSM.

## Appendix A — Viva demo script
1. Register (password path on a sensor-less laptop; narrate fingerprint path).
2. "AC sleeper Bangalore to Chennai tomorrow" → bus cards.
3. "My exam is at 7 AM" → select the 23:30 bus → THIN_BUFFER warning → switch.
4. "Book for my mother" → capture → remember → rebook zero-form.
5. Pay in test mode → ticket code → conductor Verify page → valid, then duplicate rejected.
6. Track page (SIMULATION badge) → Dashboard (warnings chart) → Profile delete.
