# T10 — Simulated GPS tracking map

**Lane:** D · **Blocked by:** T01 · **Blocks:** T11

## Summary
The report's real-time tracking, honestly simulated (ADR-013).

## Scope
- Route polylines + stop coordinates in seed data ( Majestic–Chennai corridor etc.).
- Background worker advances each in-service bus along its polyline by schedule speed; positions persisted/timestamped.
- Live map endpoint: bus positions + ETA to each stop; "simulation" badge in the UI.
- Passenger-facing map page: Leaflet + OpenStreetMap tiles (free, no key), selected bus marker + ETA.

## Acceptance
- [ ] Buses visibly move along the correct route on the map during a demo.
- [ ] ETA to the user's chosen boarding point is shown and consistent with the schedule.
- [ ] Simulation badge visible (disclosure requirement).
- [ ] Positions API is cheap to poll (no N+1, cached between worker ticks).
