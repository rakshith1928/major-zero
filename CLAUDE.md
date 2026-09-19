# CLAUDE.md — ZeroBus

Conversational bus-ticketing prototype (VTU project): FastAPI backend + React 19/Vite frontend, Supabase Postgres prod / SQLite dev. Live on Firebase Hosting + Render free tier (`render.yaml` auto-deploys on push to `main`).

**Full operator manual: [`AGENTS.md`](AGENTS.md)** — read it before any backend, frontend, or deploy work. It covers commands, domain rules, test traps, secrets, and task recipes. The summary below is only the critical path.

## Critical path

- **Shell is Windows PowerShell 5.1; repo path has a space** — quote it. Backend venv: `& "D:\New folder (2)\.venv\Scripts\python.exe"`, tests run from `backend/`.
- **`frontend/DESIGN.MD` is authoritative for UI** — honest prototype (no fake stats), restrained motion, no new animation/icon packages.
- **Secrets:** `backend/.env` is real and gitignored — never stage or paste it. Document new vars in `backend/.env.example` + `docs/SETUP.md`.
- **Money is fake:** empty Razorpay keys = demo checkout. Never touch real payments; states are `PENDING_PAYMENT`/`PAID`/`SUPERSEDED`, rebooks create new rows.
- **External calls need stub fallbacks** (no key → stub; any error → stub, never raise). No torch/ML deps in `requirements.txt`.
- **Build-time trap:** `$env:VITE_API_URL` must be set *before* `npm run build`, or the frontend silently targets localhost.
- **Tests:** backend pytest is seam-stubbed (conftest forces sqlite); frontend tests are SSR (`useEffect` never runs) and assert literal strings — keep them intact.

## Verify before claiming done

```powershell
# backend (from backend/)
& "D:\New folder (2)\.venv\Scripts\python.exe" -m pytest tests/test_booking.py -q
# frontend (from frontend/zerobus-web)
npm test; npx tsc --noEmit; npm run lint   # 2 auth.tsx warnings are pre-existing
```
