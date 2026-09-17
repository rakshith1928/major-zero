# T08 — Razorpay test-mode payments

**Lane:** B · **Blocked by:** T02, T03 · **Blocks:** T07, T12, T13

## Summary
Real checkout UX, zero real money (ADR-007).

## Scope
- Razorpay test integration: order creation from the pre-payment state → checkout sheet → signature verification → booking marked paid.
- Payment status tracking on the booking; failure/cancel path returns to the warning/pre-payment step cleanly.
- Success screen with ticket summary; hooks the event that T07 (QR) and T12 (email) consume.

## Acceptance
- [ ] A pre-payment booking completes through the Razorpay test checkout and ends paid.
- [ ] Cancelling the checkout leaves the booking resumable at pre-payment.
- [ ] Forged/failed signature verification is rejected server-side.
- [ ] Keys live only in `.env`.
