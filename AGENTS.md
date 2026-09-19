# AGENTS.md — ZeroBus

Conversational bus-ticketing prototype (VTU project). FastAPI backend + React/Vite frontend, Supabase Postgres prod / SQLite dev. Live: Firebase Hosting frontend (`college-project-c6b6a`), Render free-tier backend (`render.yaml` Blueprint auto-deploys on push to `main`).

## Layout

- `backend/app/main.py` — registers all routers. `api/` = one module per prefix (`auth`, `booking`, `guardian`, `payments`, `tickets`, `tracking`, `warnings`, `admin`, `analytics`, `metrics`, `notifications`, `passkeys`, `passengers`). `services/` = `extractor`, `detectors`, `tracking`, `notifications`, `vault`, `fare_advice`, `passenger_ref`, `payments`. `models.py`, `config.py` (pydantic Settings from `backend/.env`), `db.py`, `seed/`.
- `backend/tests/` — pytest, seam-stubbed, no network. `frontend/zerobus-web/` — React 19 + TS + Tailwind v3; `src/api.ts` (sole API seam), `src/auth.tsx`, `src/pages/` (Landing, Chat, Tickets incl. Verify, Track, Dashboard, Profile, AuthPages), `src/components/UI.tsx` (Icon/Brand/PageHeader), `src/hooks/useReveal.ts`; `tests/` SSR suite.
- `frontend/DESIGN.MD` is authoritative for UI: honest prototype (no fake stats/ratings/testimonials), night-bus indigo/amber tokens, restrained motion, `prefers-reduced-motion` respected, no new animation/icon packages.

## Commands (Windows PowerShell 5.1; repo path has a space — always quote it)

```powershell
# backend tests (MUST run from backend/; venv is at repo root)
& "D:\New folder (2)\.venv\Scripts\python.exe" -m pytest tests/test_booking.py -q
# single test: append ::test_name. Full suite ~8 min — prefer targeted files.

# frontend (run from frontend/zerobus-web)
npm test                    # node --test via renderToStaticMarkup (useEffect never runs)
npx tsc --noEmit; npm run lint   # lint = oxlint; 2 warnings in src/auth.tsx are pre-existing
$env:VITE_API_URL="https://zerobus-api.onrender.com"; npm run build
firebase deploy --only hosting   # run from frontend/zerobus-web
```

## Backend domain rules (verify in code before changing)

- **Auth:** JWT Bearer (`zb_token` in frontend localStorage), `api/deps.py:get_current_user`. Admin = email allowlist (`ADMIN_EMAILS`); empty = nobody (fail closed). Prod CORS/WebAuthn must match the Firebase hostname or passkeys + API calls break.
- **Chat slot flow** (`api/booking.py`): extractor → repeat intent (`_is_repeat_request`, explicit places win) → compare intent (needs origin+destination, continues on cheapest date) → missing-slot questions. `passenger_ref=ambiguous` with full slots asks "for me / someone else" first — tests must follow the confirm step. Session state lives in `chat_messages` (`role=state`); pre-payment snapshot saved at select.
- **Detectors** (`services/detectors.py`, all four always run): `deadline_buffer`, `boarding_deviation`, `date_time_errors`, `passenger_mismatch`. Outcomes logged FIRED/ACCEPTED/OVERRIDDEN; alternatives must be detector-clean.
- **Money is fake by design.** Empty Razorpay keys = in-app demo checkout. States: `Booking.status` ∈ `PENDING_PAYMENT`/`PAID`/`SUPERSEDED` (free-form string). Rebooks/guardian create a new `PENDING_PAYMENT` row and mark the old `SUPERSEDED` — never mutate fares or auto-charge. Gateway tests use `FakeGateway`/stubbed HTTP (`conftest.test_mode_payments`).
- **Guardian** (`api/guardian.py`): `check` (OK/AT_RISK/NO_DEADLINE, one-time `GUARDIAN_ALERT`), `rebook` (same route only, 409 if already superseded), `simulate-delay` (in-memory override in `services/tracking.py`, single-worker-safe; public tracking still reports `simulated=True`).
- **External calls need stub fallbacks** (the `OpenRouterSlotExtractor` pattern: no key → stub; any network/parse error → stub, never raise). `requirements.txt` deliberately excludes torch/sentence-transformers; the 87MB `models/` cache stays local (gitignored + dockerignored).
- **Seed is deterministic** (`seed/buses.py`): 58 bus templates, five Bangalore-centred corridors — Chennai + Hyderabad (Vellore/Kurnool midpoints), Coimbatore (Salem) + Vijayawada (Anantapur), Mysuru direct. Fares must stay in the Rs.600–1400 band (`test_seed_buses.py` enforces it). Stats shown in UI must come from seed/code, never invented.
- **History API is additive-only** (`/api/tickets/history/list` carries route/deadline/bus fields the Guardian card needs) — don't remove keys the frontend reads. QR payloads are HMAC-signed (`ticket_secret`); never overlay/animate the QR.

## Frontend rules

- All API access goes through `src/api.ts`; add types + methods there, not inline fetches. Auth state via `useAuth()`; guest pages use `SignInPrompt`.
- **Tests assert rendered strings** (`tests/ui.test.ts`): keep "Your next trip", "Illustrative conversation", `simulated`, `no real money`, `/chat` link. SSR hides nothing (opacity-only) but `useEffect` data never loads — don't test effect-fetched content.
- Styling: `zb-*` classes in `index.css` (+ Tailwind utilities); icons only from `UI.tsx` set; scroll reveals via `useReveal` (IO-based, SSR-safe); **API URL is baked at build time** — set `$env:VITE_API_URL` *before* `npm run build` or the build silently targets `localhost:8000`.

## Env & secrets

- `backend/.env` holds real secrets and is gitignored — never `git add` it, never paste values. New vars go in `backend/.env.example` + `docs/SETUP.md`. Settings reference: `database_url`, `jwt_secret`, `fernet_master`, `ticket_secret`, `admin_emails`, `cors_origins`, `webauthn_rp_id`/`webauthn_origin`, `openrouter_api_key`/`openrouter_model` (empty = rule-based chat), `razorpay_key_id`/`razorpay_key_secret` (empty = demo checkout), `smtp_*` (empty = skip mail, never fail booking).
- `backend/tests/conftest.py` forces isolation (`DATABASE_URL=sqlite://`, test WebAuthn RP). Never fight it.
- **Render free sleeps + cold-starts (~50s)**, single worker: no cron/websockets — poll or evaluate on request.

## Task recipes

- **New chat intent:** regex + helper in `api/booking.py` near `_is_repeat_request`, RED test in `backend/tests/` first, explicit slots always win, first-timers must fall through to missing-slot questions.
- **New detector:** pure function in `services/detectors.py` + wire into `_run_detectors` + FIRED/ACCEPTED/OVERRIDDEN coverage; alternative buses must be detector-clean.
- **New endpoint:** router module + `main.py` include + auth via `get_current_user` unless public like tracking; frontend method in `api.ts`.
- **New page:** route in `App.tsx` + `Nav` entry (admin-only hidden for guests) + `PageHeader` + SSR test if it carries required disclosures. Keep every simulation/test-money disclosure visible.
