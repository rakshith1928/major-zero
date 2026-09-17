# T09 — Demand prediction, peak hours, fare indicator, crowd levels

**Lane:** C · **Blocked by:** T01 · **Blocks:** T11, T13

## Summary
The report's predictive-analytics module, trained on the seeded history (ADR-005).

## Scope
- Random Forest demand prediction (route × date × hour-of-day) + peak-hour analysis, trained on 6 months of seeded bookings; scikit-learn.
- Prediction API: per-route demand curve for a date; peak-hour flags.
- Demand-based fare indicator (lightweight multiplier hint shown on bus cards).
- Crowd level per bus = booked seats / capacity, surfaced in chat cards and bus lists.
- `research/analytics.ipynb`: training, feature importance, error metrics (MAE) → `research/results/`.

## Acceptance
- [ ] Model artifact + MAE produced by one notebook run on the seeded history.
- [ ] API returns a demand curve and peak-hour flags for a route/date.
- [ ] Bus cards show crowd level and the demand-based fare indicator.
- [ ] Prediction logic behaves sensibly on unseen dates (no crash, monotone sanity checks).
