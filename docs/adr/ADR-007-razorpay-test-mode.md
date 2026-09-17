# ADR-007: Razorpay test-mode payments

**Status:** Accepted

**Context:** A booking flow needs its most satisfying moment — payment and confirmation. The Phase 2 report names Razorpay/Stripe. Real money is impossible; a pure "booking confirmed" shortcut feels fake and breaks the flow's realism in the study.

**Decision:** Integrate Razorpay in **test mode** (free account, test keys): the full checkout UX — order creation, checkout sheet, signature verification, status update — with zero money movement.

**Alternatives considered:**
- Simulated fake gateway screen — rejected: less impressive, and Razorpay test mode is equally free.
- Skip payment entirely — rejected: loses the end-to-end moment and the study's realistic stopping point.
- Stripe — rejected: Razorpay is the India-native option named in the report and supports UPI in test mode.

**Consequences:** One free Razorpay account needed; the report discloses test mode. Booking completion (and QR generation + email) hooks the payment-success event.
