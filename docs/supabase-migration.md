# Supabase migration runbook (SQLite → Supabase Postgres)

Everything below runs locally. Nothing in this project is published anywhere; the database
password exists only in `backend/.env` (gitignored). Test mode / demo payment seam (ADR-007)
is unaffected by the database switch.

## 0. What you need

- Your Supabase project's **Session Pooler** connection string:
  Supabase Dashboard → **Connect** (or Project Settings → Database) → *Session pooler* → copy the URI.
  It looks like `postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
- Current test baseline: **111 backend tests green**; migration rehearsed end-to-end on a
  disposable local Postgres (all 15 tables, 149 465 bookings, digest-verified, sequences reset,
  app smoke test passed with a continued user id).

## 1. Put credentials in `backend/.env` only

Fill in `SUPABASE_DATABASE_URL` with the Session Pooler URI, adding the SQLAlchemy driver and
TLS parameters (encode special characters in the password, e.g. `@` → `%40`):

```
postgresql+psycopg2://postgres.<project-ref>:<encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require&connect_timeout=10
```

Leave `DATABASE_URL` untouched for now — the app keeps running on SQLite until the cutover
step. Never put the URI in chat, screenshots, shell history, or code. The `.env` is
gitignored and stays on this machine.

## 2. Sanity-check the connection (read-only)

```
cd backend
python -m scripts.check_database --connect
```

Prints server version, existing `public` tables, RLS status and public grants. It performs
no writes and never prints your credentials.

## 3. Dry-run the migration (no target contact)

```
python -m scripts.migrate_sqlite_to_postgres
```

Expect the table counts and the legacy-adjustment lines (five newer tables absent in the old
SQLite file are imported empty; missing `bookings.manual_fields` is backfilled as 0).
The source file is opened read-only; its bytes cannot change (verified by SHA-256 during
rehearsal).

## 4. Apply

Stop the backend (uvicorn) first so nothing writes during the copy. Then:

```
python -m scripts.migrate_sqlite_to_postgres --apply
```

One transaction creates all 15 tables, enables RLS, revokes `PUBLIC`/`anon`/`authenticated`
grants (no browser-facing policies — the FastAPI layer owns authorization, ADR-015), copies
rows in foreign-key order in batches, digest-verifies every table's contents, and resets
identity sequences. Any failure aborts the whole transaction; the SQLite source is never
modified. A non-empty target (existing application relations) is refused, never overwritten.

## 5. Verify and cut over

```
python -m scripts.check_database --connect
```

Then smoke-test with the app pointed at Postgres *without* editing `.env`:

```
# Git Bash: DATABASE_URL="<same URI as SUPABASE_DATABASE_URL>" uvicorn app.main:app
```

Register a user — the id must continue after the migrated ids (sequence reset proof).
When satisfied, set `DATABASE_URL` to the same URI in `backend/.env` and restart.

## 6. Rollback boundary

Until you change `DATABASE_URL`, rollback = do nothing; SQLite remains authoritative and
untouched. After cutover, `backend/zerobus.db` is still on disk as a read-only fallback —
do not modify it once the app runs on Postgres.

## 7. Not covered / follow-ups

- Original dev SQLite has known drift (`bookings.manual_fields` missing); the migration
  compensates, but the pre-migration app still crashes on occupancy search — fix before
  any further browser testing on SQLite (recorded follow-up).
- Secrets are development defaults; rotating `FERNET_MASTER`/`TICKET_SECRET` needs a
  re-encryption / re-signing plan (see ADR-015). Do not rotate during this migration.
- Later hosted schema changes must use tracked migrations, not `create_all` (one-shot
  bootstrap only). Supabase MCP advisors/migration checks were unavailable in this session.
