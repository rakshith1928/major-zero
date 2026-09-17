# T05 — Other-passenger conversational capture + opt-in memory

**Lane:** A · **Blocked by:** T02, T03, T04 · **Blocks:** T13

## Summary
The "book for my mother" experience: details asked in chat, never a form; explicit consent to remember (ADR-006).

## Scope
- Conversational capture: AI asks only for the required details of the other passenger, validating age/gender/phone as they arrive.
- Post-capture consent question: "Remember her for next time?" — yes stores her in the encrypted vault; no uses-once-and-discards.
- Saved-passengers page: view and delete any consented profile.
- Flow wiring: next "book for my mother" offers the saved profile for one-tap reuse.

## Acceptance
- [ ] Capturing a new passenger requires zero form fields — all through chat.
- [ ] Declining consent leaves no trace of that passenger in the DB.
- [ ] Consented passenger appears on the profile page, is deletable, and deletion removes all trace.
- [ ] A repeat booking for a saved passenger is zero-form (one-tap reuse).
