# T01 — Data foundation & project scaffold

**Lane:** B · **Blocked by:** — · **Blocks:** T02, T03, T04, T09, T10

## Summary
Stand up the monorepo and the deterministic data layer everything else builds on.

## Scope
- `backend/` FastAPI app skeleton with settings, health endpoint, pytest wiring (establishes the project's test conventions — first prior art).
- `frontend/` React (Vite) + Tailwind skeleton; `research/`; `docs/` already seeded.
- SQLAlchemy models + config: users, passkey_credentials, passenger_profiles (encrypted), buses, bookings, tickets, payments, warnings_log, chat_messages, notifications. SQLite in dev; MySQL connection string ready (ADR-012).
- `scripts/seed_buses.py` (ADR-005): 3–4 routes, realistic operators, AC sleeper/semi-sleeper/Non-AC, ₹600–1400, 30 days, overnight arrivals.
- `scripts/seed_history.py`: 6 months of synthetic bookings with seasonal/peak patterns, fixed seed.

## Acceptance
- [ ] `uvicorn` serves the health endpoint; React dev server renders a stub page.
- [ ] Seeded DB contains buses for all routes for 30 days incl. at least one overnight bus arriving next morning.
- [ ] History table has 6 months of bookings; rerunning seeds reproduces identical data (fixed seed).
- [ ] One pytest passes through the API seam (TestClient) to fix the convention.
