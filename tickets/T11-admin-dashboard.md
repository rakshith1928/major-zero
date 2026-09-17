# T11 — Admin dashboard

**Lane:** D · **Blocked by:** T06, T09, T10 · **Blocks:** T13

## Summary
The report's centralized dashboard: operations + ML outputs + warning analytics in one view.

## Scope
- Admin role on users; admin-only routes on the API.
- React (Recharts) dashboard: bookings count/revenue over time, occupancy per route, demand-forecast charts, peak-hour heat view, live map embed.
- Warning analytics: detector firings, accepted vs overridden rates — the "mistakes prevented" view.
- Bus/route management table (read-only listing suffices in v1).

## Acceptance
- [ ] Admin login sees all charts populated from real DB data; non-admins get 403.
- [ ] Warning analytics chart distinguishes accepted vs overridden per detector.
- [ ] Live map embed shows the same simulated positions as the passenger map.
- [ ] Dashboard loads in under ~2 s on a laptop (no unbounded queries).
