# Spec — ZeroBus: AI Zero-Form Bus Ticketing with Predictive Analytics

Continuation of the VTU Phase 2 project "AI-Based Smart Bus Ticketing System with Predictive Analytics"
(AMC Engineering College, Dept. of CSE-AIML, team: Niharika HM, Roopa M, Rakshith N, N Dilliprasad Reddy; guide: Prof. Kavita Reddy N).
This spec covers the v1 build: everything promised in the Phase 2 report that is feasible without special hardware, plus the novel research layer (zero-form booking, self-vs-other identification, Pre-Booking Mistake Predictor).

## Problem Statement

Booking a bus ticket today means filling the same personal details (name, age, gender, phone) on a form every single time, even for a logged-in regular user booking for themselves. The process is slow, repetitive, and error-prone: users pick buses that arrive too late for their deadline, choose inconvenient boarding points, or get dates/AM-PM wrong — and no system warns them before they pay. There is also no evidence for how much faster, safer, or more private an AI-driven booking experience actually is compared to a traditional flow.

## Solution

ZeroBus: a web app where a fingerprint-authenticated user books buses by chatting (text or voice). The AI extracts the trip requirements from natural language, shows matching buses as chat cards, and fills all passenger details from the user's encrypted one-time profile — zero forms for self-booking. When the user books for someone else ("book for my mother"), the AI recognizes this, asks for that person's details conversationally, and offers opt-in memory. Before payment, a Pre-Booking Mistake Predictor checks four mistake types (deadline vs arrival buffer, unusual boarding point, passenger-detail mismatch, date/time errors) and warns with a safer alternative. Tickets are QR-based and verifiable by a conductor page. A predictive-analytics module forecasts demand and peak hours, shows crowd levels, and powers an admin dashboard; a simulated GPS map shows live bus positions. A controlled user study against RedBus (stopped at the payment screen, no real money) measures booking time, manual fields, mistakes prevented, and privacy perception.

## User Stories

1. As a registered passenger, I want to log in with my fingerprint, so that I don't have to type a password.
2. As a registered passenger, I want a password fallback, so that I can still log in on devices without a fingerprint sensor.
3. As a new user, I want to enter my personal details exactly once at signup, so that I never fill them again.
4. As a registered passenger, I want to type or speak "book an AC sleeper from Bangalore to Chennai tomorrow", so that the system performs the search for me.
5. As a registered passenger, I want matching buses shown as chat cards, so that I can choose without leaving the conversation.
6. As a registered passenger, I want "book a ticket for me" to autofill all passenger details from my profile, so that booking is zero-form.
7. As a registered passenger, I want "book for my mother" to ask for her details instead of using mine, so that the ticket is correct.
8. As a user booking for someone else, I want the AI to ask only for the details actually required, so that it feels like chat, not a form.
9. As a user booking for a relative, I want to opt in to remembering their details, so that future bookings for them are zero-form too.
10. As a privacy-conscious user, I want to view and delete saved passenger profiles, so that I stay in control of stored data.
11. As a user with a deadline, I want the AI to ask "any arrival deadline?" during the conversation, so that it can protect me from late buses.
12. As a user who said "my exam is at 8 AM", I want a warning when the selected bus arrives at 7:50 AM, so that I can choose a safer option.
13. As a user who normally boards at Majestic, I want a confirmation prompt when I pick an unusual boarding point, so that I don't end up in the wrong place.
14. As a user, I want date/time mistakes (past dates, "tomorrow 8 AM" ambiguity, overnight arrival dates) flagged before payment, so that my ticket matches my intent.
15. As a user booking for myself, I want a mismatch warning if berth/seat rules conflict with my profile details (age/gender), so that boarding goes smoothly.
16. As a user, I want every warning to offer one safer alternative bus, so that fixing a mistake takes one tap.
17. As a user, I want to override any warning with a "keep" action, so that the system never blocks me.
18. As a user, I want to pay through Razorpay test mode, so that the flow feels real without spending money.
19. As a user, I want a QR-code ticket after payment, so that I can board paperlessly.
20. As a user, I want an email confirmation with ticket details after payment, so that I have a record of the trip.
21. As a user, I want a booking history page, so that I can review past and upcoming trips.
22. As a user, I want to see how crowded a bus is (seats booked vs capacity), so that I can pick a less crowded one.
23. As a user, I want to see predicted demand and peak hours for my route, so that I can travel at better times.
24. As a user, I want a fare indicator that reflects predicted demand, so that price variation makes sense to me.
25. As a user, I want a live map with bus positions and ETA, so that I can time my departure to the boarding point.
26. As a conductor, I want to scan a passenger's QR ticket with a webcam, so that verification is fast.
27. As a conductor, I want a manual ticket-code fallback, so that damaged/dark screens can still be verified.
28. As a conductor, I want duplicate or invalid tickets rejected, so that fraud is prevented.
29. As an admin, I want a dashboard of bookings, revenue, and occupancy, so that I can monitor operations.
30. As an admin, I want demand-forecast charts, so that I can plan capacity per route.
31. As an admin, I want warning analytics (fired / accepted / overridden), so that I understand where users go wrong.
32. As a team member, I want a small page where classmates donate labeled utterances, so that I can build the classifier dataset.
33. As a team member, I want the classifier evaluated against Gemini zero-shot on the same held-out set, so that the paper has a fair head-to-head comparison.
34. As a team member, I want booking time, manual fields typed, and warning outcomes logged automatically, so that study metrics are objective.
35. As a study participant, I want a written consent form, so that I know how my data is used.
36. As a team member, I want participants to compare ZeroBus with RedBus (stopped at the payment screen), so that improvements are measurable and no real money is spent.
37. As a project guide, I want the final report content in the VTU chapter structure, so that submission requirements are met.

## Implementation Decisions

- **Platform & auth:** Web app (React + Vite + Tailwind). Login via WebAuthn passkeys (real fingerprint through Windows Hello) using py_webauthn server-side and @simplewebauthn/browser client-side; argon2 password fallback; JWT sessions.
- **Zero-form identity:** One-time profile entry at onboarding stored in a Fernet-encrypted passenger vault keyed per user; every vault decryption is written to an audit log.
- **Conversational core:** FastAPI backend. Gemini free tier with structured-JSON output extracts slots {origin, destination, date, bus_type, budget, deadline_time, boarding_point, passenger_ref} and drives dialogue; the AI proactively asks for arrival deadlines. Voice input via the free browser Web Speech API feeding the same chat pipeline. A persisted booking state machine survives partial conversations.
- **Inventory:** Synthetic dataset — 3–4 South-Indian routes, realistic operator names, AC sleeper/semi-sleeper/Non-AC seater, ₹600–1400, 30-day schedule including overnight buses arriving next morning. Declared as simulated in the report.
- **Self-vs-other identification (research core):** A locally trained classifier — sentence-transformer `all-MiniLM-L6-v2` embeddings + logistic-regression head (scikit-learn) over utterances labeled self / other / ambiguous. Gating: self → vault autofill; other → conversational capture + opt-in "remember her for next time?" stored encrypted with view/delete UI; ambiguous → clarifying question. Evaluated head-to-head against Gemini zero-shot on the same held-out set (confusion matrix, precision/recall/F1).
- **Minimal-download model policy:** No ML artifacts are downloaded until the classifier step. The HF cache is redirected to `D:\New folder (2)\models\huggingface` via HF_HOME/SENTENCE_TRANSFORMERS_HOME; the only download is all-MiniLM-L6-v2 (~90 MB), fetched once, then loaded offline.
- **Pre-Booking Mistake Predictor:** Four detectors as pure functions over (slots, bus, profile, history): deadline-vs-arrival buffer, boarding-point deviation from per-route history, passenger-detail mismatch (classifier + age/gender berth rules), date/time errors. Every warning is logged to warnings_log with outcome (fired / accepted / overridden) and offers one safer alternative.
- **Ticketing & payment:** QR ticket generated per confirmed booking; conductor verification page with webcam scanning (html5-qrcode) plus manual code fallback; duplicate/invalid rejection. Razorpay test-mode checkout. Email confirmation via SMTP + in-app notification; booking history page.
- **Predictive analytics:** Random Forest demand prediction (route × date × hour) and peak-hour analysis trained on 6 months of seeded synthetic bookings; demand-based fare indicator; crowd level = booked seats / capacity.
- **Tracking & dashboard:** Simulated GPS — a background worker advances buses along route polylines; Leaflet + OpenStreetMap live map with ETA (disclosed as simulation). Admin dashboard in React (Recharts): bookings, revenue, occupancy, demand forecasts, warning analytics, live map.
- **Database:** SQLAlchemy ORM; SQLite file for development, MySQL for the final demo (one config switch).
- **Testing seams:** (1) the FastAPI HTTP API is the highest seam — behavior tests via TestClient with a stubbed SlotExtractor returning canned slot JSON; (2) the classifier is a black-box seam evaluated by metrics on a held-out labeled set, never by implementation details; (3) each detector is a pure seam tested with positive and negative (no-false-alarm) cases; (4) QR generation/verification tested as an end-to-end round trip through the API; (5) seed scripts are deterministic (fixed seed). Prior art: none (greenfield) — pytest conventions are established in the data-foundation ticket.
- **Research protocol:** Within-subject study, 16–20 participants, counterbalanced order; baseline = real RedBus stopped at the payment screen (no real money); RedBus-familiarity survey as covariate; scripted scenarios with planted mistakes; metrics: booking time (start → pre-payment confirmation), manual fields typed, task success, warning outcomes, SUS + privacy-perception Likert. Written consent for all participants.

## Out of Scope

Real GPS fleet integration (v1 simulates positions); CCTV/computer-vision crowd detection (v1 uses booked-seats/capacity); NFC/RFID validation; SMS notifications; facial recognition; native mobile app; multilingual support; offline ticket validation; automated route optimization; AI Requirement Negotiator; conversation Undo/version system; real (non-test) payments; production deployment. All deferred items map to the Phase 2 report's own Chapter 7 "Planned Enhancements" and stay future work.

## Further Notes

- Deliverables: working v1, docs (glossary + ADRs + this spec), final report content in the Phase 2 report's exact VTU chapter structure (new AI modules presented as Phase 3 additions), and a research paper draft (`research/paper.md`).
- Disclosures that must appear in the report: synthetic bus inventory, simulated GPS tracking, Razorpay test mode, RedBus cutoff protocol.
- No git/GitHub/remote — all artifacts live as local files in this workspace by explicit decision.
- Suggested 4-way ownership: chatbot/voice/booking · auth/vault/QR/payments · ML (classifier + demand + detectors) · frontend/dashboard/study.
