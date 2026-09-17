# T03 — Chat booking: slot extraction, search, booking state machine

**Lane:** A · **Blocked by:** T01, T02 · **Blocks:** T05, T06, T08, T13

## Summary
The conversational core: user says what they want, matching buses come back as chat cards, a booking can be driven to the pre-payment state (ADR-004).

## Scope
- Gemini client behind a `SlotExtractor` seam (canned JSON stub for tests): outputs {origin, destination, date, bus_type, budget, deadline_time, boarding_point, passenger_ref}.
- Dialogue loop that asks for missing slots and **proactively asks for arrival deadlines**.
- Inventory search API (filters + ranking) over seeded buses; results as chat cards (price, type, departure/arrival, duration, crowd level stub).
- Persisted booking state machine: searching → results → bus selected → passenger set → pre-payment.
- Voice input via Web Speech API feeding the same text pipeline (ADR-003).

## Acceptance
- [ ] "Book an AC sleeper from Bangalore to Chennai tomorrow" yields matching bus cards in chat.
- [ ] With a deadline stated, the conversation records `deadline_time`.
- [ ] A booking reaches the pre-payment state and survives a page reload (persisted state machine).
- [ ] API behavior tests pass with the stubbed SlotExtractor (no network in tests).
