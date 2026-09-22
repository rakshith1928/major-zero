# ZeroBus Setup Guide

Local development setup for the ZeroBus prototype (FastAPI backend + React/Vite frontend).
Everything runs on your machine; the database is your Supabase project over its session pooler.

## Prerequisites

- Python 3.12+ with the workspace virtual environment at `.venv/` (created once: `python -m venv .venv`)
- Node.js 22.13+ (the `node --test` TypeScript suites need it) and npm
- A Supabase project (or fall back to a local SQLite file for quick experiments)

## 1. Backend configuration

```bash
copy backend\.env.example backend\.env
```

Fill in `backend/.env` (never commit this file):

| Key | Purpose |
|---|---|
| `DATABASE_URL` | Active database. Supabase: `postgresql+psycopg2://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require&connect_timeout=10` |
| `SUPABASE_DATABASE_URL` | Migration target for `scripts/migrate_sqlite_to_postgres.py` |
| `JWT_SECRET`, `FERNET_MASTER`, `TICKET_SECRET` | Generate each with `python -c "import secrets; print(secrets.token_urlsafe(48))"` (keep them 32+ bytes) |
| `HF_HOME` | Point at `models/huggingface`; the app runs with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | Test-mode keys only. Left empty, the app shows the built-in demo checkout |
| `ADMIN_EMAILS` | Comma-separated emails that see the admin dashboard |

Install dependencies and start the API on port 8000:

```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
```

Health check: <http://localhost:8000/health>

## 2. Frontend

```bash
cd frontend/zerobus-web
npm install
npm run dev
```

Open <http://localhost:5173>. The frontend calls `http://localhost:8000` by default;
override with `VITE_API_URL` in `frontend/zerobus-web/.env` if needed.

## Live environments

| | URL |
|---|---|
| App (Firebase Hosting) | <https://college-project-c6b6a.web.app> |
| API (Render, free tier) | <https://zerobus-api.onrender.com> |

- Backend deploys from `render.yaml` (Blueprint) on every push to `main`;
  first request after idle cold-starts (~50s).
- Frontend: `cd frontend/zerobus-web && $env:VITE_API_URL="https://zerobus-api.onrender.com"; npm run build; firebase deploy --only hosting`
- Prod-only env vars (Render dashboard, never committed): `DATABASE_URL`,
  `JWT_SECRET`, `FERNET_MASTER`, `TICKET_SECRET`, `OPENROUTER_API_KEY`
  (empty = rule-based chat), `CORS_ORIGINS`, `WEBAUTHN_RP_ID`,
  `WEBAUTHN_ORIGIN`, `ADMIN_EMAILS`.

## 3. Database migration (SQLite → Supabase)

Only needed once per project. The tool is read-only by default:

```bash
cd backend
../.venv/Scripts/python.exe -m scripts.check_database          # offline validation
../.venv/Scripts/python.exe -m scripts.migrate_sqlite_to_postgres   # dry run
../.venv/Scripts/python.exe -m scripts.migrate_sqlite_to_postgres --apply
```

Full runbook: [docs/supabase-migration.md](supabase-migration.md).
After a verified apply, set `DATABASE_URL` to the Supabase URI.

## 4. Tests

```bash
# Backend (run from backend/)
../.venv/Scripts/python.exe -m pytest

# Frontend (run from frontend/zerobus-web/)
npm test     # node --test
npm run lint # oxlint
npx tsc --noEmit
npm run build
```

## 5. Seed data

`backend/app/seed/` ships the simulated bus inventory (82 buses across eight
Bangalore-centred corridors: Chennai, Hyderabad, Mysuru, Coimbatore,
Vijayawada, Goa, Tirupati, Pondicherry) and booking history used by the
prototype. The seed scripts are idempotent helpers, not production data.

## Ground rules baked into this project

- Secrets live only in `backend/.env`; nothing is published or pushed anywhere.
- Razorpay stays in **test mode** — no real money moves, demos stop at the payment screen.
- The passenger-intent MiniLM model is local-only (`docs/LOCAL_ML.md`); production uses keyword rules.
- Bus inventory, GPS positions, and crowd levels are **simulated** and labelled as such in the UI.
- Hugging Face models load from the local cache only (offline mode).
