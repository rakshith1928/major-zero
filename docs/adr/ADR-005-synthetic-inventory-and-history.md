# ADR-005: Synthetic bus inventory + 6-month synthetic booking history

**Status:** Accepted

**Context:** RedBus offers no free public API; scraping breaches their ToS and prices shift mid-study. Hand-copied real listings are stale and can't be controlled. The Mistake Predictor and the demand model both need *controlled* data (e.g., a bus that arrives 7:50 for an 8:00 deadline; six months of bookings with peaks).

**Decision:** Generate the inventory and history deterministically: 3–4 South-Indian routes (Bangalore↔Chennai, Bangalore↔Hyderabad, …), realistic operator names (VRL/KPN/SRS-style), AC sleeper / AC semi-sleeper / Non-AC seater, ₹600–1400, a 30-day schedule including overnight buses arriving the next morning, plus 6 months of seeded bookings with seasonal/peak patterns for the demand model. Fixed random seed; generator scripts live in `scripts/`.

**Alternatives considered:**
- Scraping RedBus — rejected: ToS, fragility, moving prices.
- Hand-copied real listings — rejected: tedious, stale, uncontrollable for staged scenarios.

**Consequences:** Full experimental control and reproducibility; the report must explicitly disclose the inventory as simulated.
