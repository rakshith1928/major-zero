# T06 — Pre-Booking Mistake Predictor (4 detectors)

**Lane:** C · **Blocked by:** T03, T04 · **Blocks:** T11, T13

## Summary
The differentiator: catch likely booking mistakes before payment, log every outcome (ADR-001).

## Scope
- Four detectors as **pure functions** over (slots, bus, passenger details, history):
  1. Deadline vs arrival buffer (fires when margin too thin, e.g., arrival 7:50 for 8:00 deadline).
  2. Boarding-point deviation (chosen point differs from the user's per-route history).
  3. Passenger-detail mismatch (classifier/profile conflicts; age/gender berth rules).
  4. Date/time errors (past dates, "tomorrow 8 AM" departure-vs-arrival ambiguity, overnight arrival dates).
- `warnings_log` rows: detector, booking, fired, outcome = fired / accepted (changed) / overridden (kept).
- Pre-payment ⚠️ card UI: reason in plain words + "keep" and "change" actions + **one safer alternative bus** pre-computed.
- Detector test suites incl. negative cases (clean scenarios produce no warning — false-alarm control).

## Acceptance
- [ ] Each detector has positive + negative tests through its pure seam.
- [ ] Staged scenario (8 AM deadline, 7:50 arrival bus) fires the buffer warning and offers a safer bus.
- [ ] "Keep" proceeds to payment; "change" swaps to the alternative; both outcomes hit `warnings_log`.
