# ADR-014: Notifications — email via SMTP + in-app; SMS deferred

**Status:** Accepted

**Context:** The Phase 2 report lists SMS/email notification APIs. SMS requires a paid provider (e.g., Twilio) or gateway credits — outside the zero-budget constraint.

**Decision:** Booking confirmations and travel alerts are delivered by **email (Gmail SMTP with an app password)** and as **in-app notifications**. SMS is documented as future work.

**Alternatives considered:**
- Twilio/MSG91 SMS — rejected: recurring cost for marginal demo value.
- No notifications — rejected: email is nearly free and satisfies the report line.

**Consequences:** The notifications checkbox is covered at zero cost; the report notes SMS as a planned enhancement. The SMTP credential lives in `.env`, never in code.
