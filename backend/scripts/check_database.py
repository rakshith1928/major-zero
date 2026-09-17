"""Verify the configured Supabase target: offline by default, --connect to probe."""
import argparse

from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

from scripts.migrate_sqlite_to_postgres import BACKEND, MigrationError, validate_target


def load_config():
    return dotenv_values(BACKEND / ".env")
def describe(url):
    return f"{url.drivername}://{url.host}:{url.port}/{url.database} (user {url.username})"


def probe(target):
    engine = create_engine(target, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
            server = conn.execute(text("SHOW server_version")).scalar()
            inspector = inspect(conn)
            existing = sorted(inspector.get_table_names(schema="public"))
            rls = conn.execute(text(
                "SELECT c.relname, c.relrowsecurity FROM pg_catalog.pg_class c "
                "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' ORDER BY 1"
            )).all()
            grants = conn.execute(text(
                "SELECT grantee, privilege_type FROM information_schema.role_table_grants "
                "WHERE table_schema = 'public' AND grantee IN ('PUBLIC','anon','authenticated') LIMIT 20"
            )).all()
            print(describe(target))
            print(f"server_version: {server}")
            print("application tables:", ", ".join(existing) if existing else "(none)")
            print("RLS enabled:", ", ".join(name for name, enabled in rls if enabled) or "(none)")
            print("public grants:", ", ".join(f"{grantee}:{priv}" for grantee, priv in grants) or "(none)")
    finally:
        engine.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connect", action="store_true", help="Read-only live probe of the configured target")
    args = parser.parse_args(argv)
    try:
        target = validate_target(load_config().get("SUPABASE_DATABASE_URL"))
        if not args.connect:
            print("Configuration valid; no connection attempted.")
            print(describe(target))
            return 0
        probe(target)
        return 0
    except MigrationError as exc:
        print(f"Check stopped: {exc}")
        return 1
    except Exception:
        print("Check stopped: connection or query failure; no connection strings or credentials logged.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
