# ADR-008: Research baseline — real RedBus with cutoff at the payment screen

**Status:** Accepted

**Context:** The metrics (booking time, fields entered, errors, satisfaction) need a baseline. Building a form-based twin app gives perfect control but weaker external validity; the team chose the real RedBus. Real completed bookings would cost ₹300–700 per participant and create refund hassle.

**Decision:** Participants perform scripted tasks on the live RedBus site in a browser and **stop at the payment screen** — no real money. On ZeroBus the flow ends at the equivalent pre-payment confirmation (payment itself is Razorpay test mode). Timing/field metrics are measured to that equivalent point on both systems. A short survey records each participant's prior RedBus familiarity, used as a covariate; system order is counterbalanced; written consent is collected.

**Alternatives considered:**
- Self-built form-based twin app — rejected by the team despite better control.
- Real completed RedBus bookings — rejected: real money per participant, cancellation hassle.
- RedBus for qualitative notes only — rejected: weakest paper; reviewers ask "faster than what?"

**Consequences:** External validity with a fair, money-free comparison. Residual variance (network, ads, RedBus UI changes) is handled by counterbalancing, medians, and the familiarity covariate — documented as a threat to validity in the paper.
