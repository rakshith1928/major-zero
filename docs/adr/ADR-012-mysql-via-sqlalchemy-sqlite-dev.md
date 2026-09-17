# ADR-012: Database — MySQL via SQLAlchemy, SQLite in development

**Status:** Superseded by ADR-015 (final-demo database is Supabase Postgres, not MySQL)

**Context:** The Phase 2 report names MySQL/Firebase as the database layer. Firebase Auth would conflict with the WebAuthn passkey design; installing MySQL is only needed for the final demo, and developing against a local MySQL server slows iteration.

**Decision:** All data access goes through **SQLAlchemy ORM models**. Development runs on a SQLite file; the final demo runs on **MySQL** — switching is one connection-string change in config. Schema: users, passkey_credentials, passenger_profiles (encrypted), buses, bookings, tickets, payments, warnings_log, chat_messages, notifications.

**Alternatives considered:**
- Firebase/Firestore — rejected: auth lock-in conflicts with WebAuthn, weaker local testing story.
- SQLite everywhere — rejected: deviates from the report's stated stack for no effort saved (the ORM already exists).

**Consequences:** Report alignment ("MySQL") with zero dev friction; ORM migrations keep both backends compatible.
