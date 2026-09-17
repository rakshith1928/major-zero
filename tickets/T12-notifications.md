# T12 — Email + in-app notifications

**Lane:** A · **Blocked by:** T08 · **Blocks:** T13

## Summary
Report checkbox for notifications, at zero cost (ADR-014).

## Scope
- Email confirmation on payment success: ticket summary + QR link, via Gmail SMTP + app password from `.env`.
- In-app notification center (bell): payment success, upcoming-trip reminder for tomorrow's bookings.
- Notification rows persisted in the notifications table; failures logged, never blocking the booking flow.

## Acceptance
- [ ] Paying sends a formatted email containing the ticket summary.
- [ ] Notification center shows payment + reminder entries.
- [ ] SMTP outage does not fail the booking (graceful degradation).
