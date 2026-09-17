# ADR-015: Supabase Postgres replaces the planned MySQL deployment

**Status:** Accepted design; hosted migration pending credentials and verification (2026-09-17).

## Context

ZeroBus uses SQLAlchemy and an existing local SQLite database. The user requested Supabase migration and a local `.env`. The Supabase plugin is configured, but its MCP tools are not exposed in this session; no project connection has been verified. No hosted schema or data has been changed. All implementation work remains local, with no git or publication.

## Decision

- Supabase Postgres is the intended hosted database, superseding ADR-012's MySQL choice. SQLite remains an offline/test fallback and the migration source; it is not removed before a verified cutover.
- FastAPI and SQLAlchemy continue to own authentication, authorization, vault access and payments. The TypeScript frontend does not receive a database password or Supabase service key and does not use PostgREST directly.
- `DATABASE_URL` selects the active database. `SUPABASE_DATABASE_URL` stages the target independently, so preparing a migration cannot accidentally switch the running application. Both belong only in `backend/.env`.
- Prefer the project's Session Pooler connection on port 5432 for IPv4 compatibility. Use `postgresql+psycopg2`, TLS and a finite connection timeout; copy the actual host from the project's Connect dialog.
- `build_engine()` applies SQLite-only connection options only to SQLite; Postgres uses connection pre-ping. The driver is pinned in `requirements.txt`.
- A one-shot, explicitly invoked migration bootstraps fresh tables in `public`. Default invocation only reads the SQLite source. Apply mode refuses existing application relations; it does not merge, truncate or overwrite.
- The migration preserves IDs and encrypted/signed payloads, imports in foreign-key order, validates copied content/counts and resets integer sequences. Known legacy missing fields are handled explicitly rather than modifying the source or silently dropping unknown data.
- Enable RLS without browser-access policies and revoke public/anonymous/authenticated access to application tables. The privileged server-side database connection retains API-layer authorization. Do not expose these tables directly to Supabase browser clients.
- `create_all()` is only for the initial empty-target bootstrap, not future upgrades. Later hosted schema changes must use tracked migrations after inspecting the actual project and migration history. MCP migration/advisor checks are blocked until those tools are available.

## Consequences and limitations

The connection string is not the entire migration: schema creation, source validation, transfer and live Postgres verification precede cutover. Existing source SQLite has legacy drift, including missing `bookings.manual_fields`; startup does not fix it.

Preserve the existing `FERNET_MASTER`, `TICKET_SECRET` and user IDs during transfer. Changing these may make vault data unreadable or invalidate tickets. Existing development secrets are not deployment-ready; secure rotation is a separate migration, not an incidental edit.

Local tests use SQLite and test doubles. They do not establish hosted Postgres compatibility, TLS connectivity, effective Supabase grants, or correctness under multiple API worker processes. Keep the study/demo single-worker and test-mode only until broader deployment validation is performed.

See [the migration runbook](../supabase-migration.md) for preparation, verification, cutover and rollback boundaries.
