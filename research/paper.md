# ZeroBus: Context-Aware Zero-Form Bus Booking with Pre-Booking Mistake Prevention

## Abstract
Booking an intercity bus still means filling the same passenger form on every
trip, even for a logged-in user booking for themselves. We present ZeroBus, a
conversational bus-ticketing system that (1) authenticates with WebAuthn
passkeys (fingerprint), (2) autofills the passenger from an encrypted
one-time profile when the ticket is for the authenticated user, (3) detects
whether the ticket is for the user or someone else with a locally trained
classifier, and (4) warns about likely mistakes *before* payment. On a
held-out set of 114 utterances our MiniLM-embedding + logistic-head
classifier reaches 93.9% accuracy (macro F1 0.937). A RandomForest demand
model trained on 6,120 synthetic route-day rows predicts occupancy with
MAE 0.077. A within-subject study protocol against RedBus (cut off at the
payment screen, no real money) measures booking time, manual fields typed,
mistakes prevented, and privacy perception.

## 1. Introduction
Repeated passenger-data entry is the dominant friction in online bus booking.
Forms ask for name, age, gender, and phone on every trip, and mistakes (wrong
date, late arrival, wrong boarding point) surface only after payment. ZeroBus
moves the booking into a chat where identity is established once by
fingerprint and context does the rest.

## 2. Related Work
Conversational booking assistants; biometric WebAuthn adoption; demand
forecasting for public transport (RandomForest / time-series); error
prevention in e-commerce checkout flows; QR ticketing and fraud.

## 3. Method
**Architecture.** FastAPI + SQLAlchemy backend (SQLite dev, MySQL demo),
React + Vite + Tailwind frontend, Gemini free tier for slot extraction as
structured JSON, deterministic rule stubs for offline tests.

**Passenger-reference identification.** 1,020 labeled utterances
(self/other/ambiguous; hand templates + paraphrase + classmate collection via
`collect.html`). Frozen `all-MiniLM-L6-v2` embeddings (the only HF download,
~90 MB, cached on disk, offline afterwards) + scikit-learn logistic head,
stratified 80/20 split. Head-to-head protocol against Gemini zero-shot on the
identical 114 held-out items (`eval_gemini_zero_shot.py`; Gemini row fills in
when `GEMINI_API_KEY` is set).

**Mistake Predictor.** Four pure-function detectors over
(slots, bus, passenger, history): deadline-vs-arrival buffer (<45 min warns,
arrival after deadline warns harder), boarding-point deviation from per-route
history, passenger-detail mismatch (age/gender berth rules), date/time errors
(past dates, overnight-arrival confusion). Every firing is logged with outcome
FIRED / ACCEPTED / OVERRIDDEN and offers one safer alternative bus.

**Ticketing & payment.** HMAC-signed QR payloads, single-use verification by
a conductor page, Razorpay test-mode checkout (no real money), SMTP + in-app
notifications with graceful mail degradation.

## 4. Results
- Passenger-ref classifier: **accuracy 0.939, macro F1 0.937** (held-out n=114).
- Demand model: **MAE 0.077** over 6,120 route-day rows; weekday dominates
  importance (0.966), matching the seeded weekend peak.
- Backend suite: all endpoint tests green (auth incl. full WebAuthn ceremony
  against a soft authenticator, booking, payments, tickets, detectors,
  analytics, tracking, admin, notifications, metrics).
- Frontend: TypeScript strict (`tsc --noEmit` clean), production build green.

## 5. User Study (protocol, T13)
Within-subject, counterbalanced, n=16–20. Baseline: live RedBus stopped at
the payment screen. Five scripted tasks with planted mistakes
(`induced_scenarios.json`). Metrics: booking seconds (start → pre-payment),
manual fields typed, task success, warning outcomes, SUS per system, privacy
Likert, familiarity covariate. Analysis: paired Wilcoxon + summary tables
(`analysis_template.py`).

## 6. Threats to Validity
Synthetic inventory and simulated GPS limit ecological validity (both
disclosed in-app and in the report); RedBus UI drift adds baseline variance
(counterbalancing + medians mitigate); Gemini quota during the study is
handled by caching extractions and a fallback model.

## 7. Future Work
Requirement Negotiator (relax which constraint), conversation Undo/versions,
real GPS fleet feed, CCTV crowd detection, SMS, facial recognition,
multilingual UI — all mapped to Phase 2 report Chapter 7.
