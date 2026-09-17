"""Read-only preflight by default; --apply bootstraps an empty Postgres target."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3

from dotenv import dotenv_values
from sqlalchemy import MetaData, create_engine, func, inspect, literal, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

BACKEND = Path(__file__).resolve().parents[1]
LEGACY_TABLES = {"metric_rows", "vault_audit_log", "pending_passengers", "metric_starts", "webauthn_challenges"}
LEGACY_COLUMNS = {("bookings", "manual_fields"), ("metric_rows", "manual_fields")}


class MigrationError(Exception):
    pass


def _metadata():
    # Imported lazily: app.config loads backend/.env at import time, and a
    # malformed value there must surface as a sanitized MigrationError rather
    # than a pydantic traceback that could echo configuration input.
    try:
        from app import models  # noqa: F401
        from app.db import Base
    except Exception:
        raise MigrationError("application configuration failed to load; check backend/.env") from None
    return Base.metadata


def load_config():
    return dotenv_values(BACKEND / ".env")


def validate_target(value):
    try:
        url = make_url(value or "")
        if url.drivername != "postgresql+psycopg2" or not url.host or not url.database:
            raise ValueError()
        loopback = url.host in {"127.0.0.1", "::1", "localhost"}
        sslmode = url.query.get("sslmode")
        if loopback and sslmode == "disable":
            # Rehearsal exemption: a disposable local cluster has no TLS. Only
            # plain host/port/db/sslmode/connect_timeout may be set — libpq
            # overrides like hostaddr or options could redirect the socket to
            # a non-loopback destination while the URL still says localhost.
            if set(url.query) - {"sslmode", "connect_timeout"}:
                raise ValueError()
        elif sslmode not in {"require", "verify-ca", "verify-full"}:
            raise ValueError()
        if not 1 <= int(url.query.get("connect_timeout", "0")) <= 60:
            raise ValueError()
        return url
    except Exception:
        raise MigrationError("target configuration invalid; require psycopg2, TLS (loopback may disable) and connect_timeout=1..60") from None


@contextmanager
def source_snapshot(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise MigrationError("source database not found")
    # A URI opened by sqlite3 enforces read-only access independently of SQLAlchemy.
    from sqlalchemy import create_engine as sqlite_engine
    engine = sqlite_engine("sqlite://", creator=lambda: sqlite3.connect(path.as_uri() + "?mode=ro", uri=True), poolclass=NullPool)
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("BEGIN")
            yield conn
            conn.rollback()
    finally:
        engine.dispose()


def inventory(conn):
    metadata = _metadata()
    if conn.exec_driver_sql("PRAGMA integrity_check").scalar() != "ok":
        raise MigrationError("source integrity check failed")
    if conn.exec_driver_sql("PRAGMA foreign_key_check").first():
        raise MigrationError("source foreign-key check failed")
    inspector = inspect(conn)
    existing = set(inspector.get_table_names())
    expected = set(metadata.tables)
    if existing - expected or (expected - existing) - LEGACY_TABLES:
        raise MigrationError("source schema has unexpected or missing tables")
    counts, adjustments = {}, []
    for table in metadata.sorted_tables:
        if table.name not in existing:
            counts[table.name] = 0
            adjustments.append(f"{table.name}: empty (legacy table absent)")
            continue
        actual = {c["name"] for c in inspector.get_columns(table.name)}
        wanted = set(table.c.keys())
        if actual - wanted or any((table.name, c) not in LEGACY_COLUMNS for c in wanted - actual):
            raise MigrationError(f"source schema mismatch: {table.name}")
        adjustments.extend(f"{table.name}.{c}=0" for c in sorted(wanted - actual))
        # Boolean columns must hold a pure 0/1 domain: SQLite tolerates other
        # integers, and the typed read below would coerce them silently.
        for column in table.c:
            if column.type.python_type is bool:
                bad = conn.scalar(select(func.count()).select_from(table).where(column.notin_((0, 1))))
                if bad:
                    raise MigrationError(f"source contains non-boolean values in {table.name}.{column.name}")
        counts[table.name] = conn.scalar(select(func.count()).select_from(table))
        # Validate model FKs even when an old SQLite schema omitted constraints.
        for fk in table.foreign_keys:
            parent = fk.column.table
            if parent.name not in existing:
                if conn.scalar(select(func.count()).select_from(table).where(fk.parent.is_not(None))):
                    raise MigrationError("source contains orphaned references")
            elif conn.execute(select(fk.parent).select_from(table.outerjoin(parent, fk.parent == fk.column)).where(fk.parent.is_not(None), fk.column.is_(None)).limit(1)).first():
                raise MigrationError("source contains orphaned references")
    return {"counts": counts, "adjustments": adjustments}


def table_digest(rows, table, digest=None):
    """Order-independent content digest over canonicalized row values.

    Source and target each order rows by their own primary-key collation, so
    the accumulator XORs per-row hashes instead of hashing an ordered stream.
    Values pass through json.dumps(default=str) once per row, matching what
    the other side reads back after the database round-trip.
    """
    acc = int.from_bytes(digest or b"\x00" * 32, "big")
    for row in rows:
        data = json.dumps([row[c.name] for c in table.c], default=str, ensure_ascii=True, separators=(",", ":")).encode()
        value = hashlib.sha256(len(data).to_bytes(8, "big") + data).digest()
        acc ^= int.from_bytes(value, "big")
    return acc.to_bytes(32, "big")


def source_rows(conn, table):
    inspector = inspect(conn)
    if not inspector.has_table(table.name):
        return
    actual = {c["name"] for c in inspector.get_columns(table.name)}
    columns = [c if c.name in actual else literal(0, type_=c.type).label(c.name) for c in table.c]
    result = conn.execute(select(*columns).select_from(table).order_by(*table.primary_key.columns))
    for rows in result.mappings().partitions(1000):
        yield [dict(row) for row in rows]


def copy_to_target(source, target_engine):
    metadata = _metadata()
    report = inventory(source)
    if target_engine.dialect.name != "postgresql":
        raise MigrationError("target must be PostgreSQL")
    target_metadata = MetaData(schema="public")
    tables = [table.to_metadata(target_metadata, schema="public") for table in metadata.sorted_tables]
    with target_engine.begin() as dest:
        dest.execute(text("SET LOCAL lock_timeout = '10s'"))
        dest.execute(text("SET LOCAL statement_timeout = '120s'"))
        dest.execute(text("SET LOCAL search_path = public"))
        names = dest.execute(text("SELECT c.relname FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'" )).scalars().all()
        if set(names) & set(metadata.tables):
            raise MigrationError("target contains existing application relations; refusing overwrite")
        # checkfirst=False also refuses unrelated name collisions transactionally.
        target_metadata.create_all(dest, checkfirst=False)
        roles = set(dest.execute(text("SELECT rolname FROM pg_catalog.pg_roles WHERE rolname IN ('anon','authenticated')")).scalars())
        quote = dest.dialect.identifier_preparer.quote
        for table in tables:
            qualified = 'public.' + quote(table.name)
            dest.execute(text(f"ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY"))
            for role in ["PUBLIC", *sorted(roles)]:
                dest.execute(text(f"REVOKE ALL ON TABLE {qualified} FROM {quote(role) if role != 'PUBLIC' else role}"))
            source_table = metadata.tables[table.name]
            source_digest = None
            for rows in source_rows(source, source_table):
                source_digest = table_digest(rows, source_table, source_digest)
                dest.execute(table.insert(), rows)
            copied = dest.scalar(select(func.count()).select_from(table))
            if copied != report["counts"][table.name]:
                raise MigrationError("target count verification failed")
            target_digest = None
            result = dest.execution_options(stream_results=True).execute(select(table))
            for rows in result.mappings().partitions(1000):
                target_digest = table_digest(rows, table, target_digest)
            result.close()
            dest.execution_options(stream_results=False)
            if source_digest != target_digest:
                raise MigrationError("target content verification failed")
            pk = list(table.primary_key.columns)
            if len(pk) == 1 and pk[0].type.python_type is int:
                sequence = dest.scalar(text("SELECT pg_get_serial_sequence(:table, :column)"), {"table": qualified, "column": pk[0].name})
                maximum = dest.scalar(select(func.max(pk[0])))
                if sequence:
                    dest.execute(text("SELECT setval(CAST(:seq AS regclass), :value, :called)"), {"seq": sequence, "value": max(maximum or 1, 1), "called": maximum is not None})
                    for role in ["PUBLIC", *sorted(roles)]:
                        dest.execute(text(f"REVOKE ALL ON SEQUENCE {sequence} FROM {quote(role) if role != 'PUBLIC' else role}"))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Explicitly authorize transfer to configured hosted target")
    parser.add_argument("--dry-run", action="store_true", help="Read local source only (default)")
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        parser.error("choose --apply or --dry-run, not both")
    engine = None
    try:
        config = load_config()
        with source_snapshot(config.get("SOURCE_SQLITE_PATH") or BACKEND / "zerobus.db") as source:
            report = inventory(source)
            if args.apply:
                engine = create_engine(validate_target(config.get("SUPABASE_DATABASE_URL")), poolclass=NullPool)
                report = copy_to_target(source, engine)
            print("Migration committed and content verified." if args.apply else "Dry run: local source only; no target connection or writes.")
            for name, count in report["counts"].items():
                print(f"{name}: {count}")
            for adjustment in report["adjustments"]:
                print(f"Legacy adjustment: {adjustment}")
        return 0
    except MigrationError as exc:
        print(f"Migration stopped: {exc}")
        return 1
    except Exception:
        print("Migration stopped: database or data validation failure; no connection strings or row data logged.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
