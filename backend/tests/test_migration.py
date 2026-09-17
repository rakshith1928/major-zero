from datetime import datetime
import hashlib

import pytest
from sqlalchemy import create_engine, inspect, select, text

from app.db import Base
from app.models import User


def source_database(tmp_path):
    path = tmp_path / "source.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(User.__table__.insert(), {
            "id": 17, "email": "migration@example.invalid", "is_admin": False,
            "is_synthetic": True, "created_at": datetime(2026, 1, 2, 3, 4, 5),
        })
    engine.dispose()
    return path


def test_dry_run_preserves_source_and_reads_typed_values(tmp_path):
    from scripts.migrate_sqlite_to_postgres import source_snapshot, inventory
    path = source_database(tmp_path)
    before = hashlib.sha256(path.read_bytes()).digest()
    with source_snapshot(path) as conn:
        report = inventory(conn)
        assert report["counts"]["users"] == 1
        assert len(report["counts"]) == 15
        row = conn.execute(select(User.__table__)).mappings().one()
        assert row["created_at"] == datetime(2026, 1, 2, 3, 4, 5)
        assert row["is_synthetic"] is True
        with pytest.raises(Exception):
            conn.execute(text("DELETE FROM users"))
    assert hashlib.sha256(path.read_bytes()).digest() == before


def test_known_legacy_drift_is_explicit(tmp_path):
    from scripts.migrate_sqlite_to_postgres import source_snapshot, inventory
    path = source_database(tmp_path)
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE bookings DROP COLUMN manual_fields"))
        conn.execute(text("DROP TABLE metric_starts"))
    engine.dispose()
    with source_snapshot(path) as conn:
        report = inventory(conn)
        assert "bookings.manual_fields=0" in report["adjustments"]
        assert "metric_starts: empty (legacy table absent)" in report["adjustments"]


def test_unknown_drift_fails_closed(tmp_path):
    from scripts.migrate_sqlite_to_postgres import source_snapshot, inventory, MigrationError
    path = source_database(tmp_path)
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN unrecognized TEXT"))
    engine.dispose()
    with source_snapshot(path) as conn, pytest.raises(MigrationError, match="schema"):
        inventory(conn)


def test_missing_source_is_not_created(tmp_path):
    from scripts.migrate_sqlite_to_postgres import source_snapshot, MigrationError
    path = tmp_path / "missing.db"
    with pytest.raises(MigrationError):
        with source_snapshot(path):
            pass
    assert not path.exists()


@pytest.mark.parametrize("url", ["", "sqlite:///file.db", "postgresql+psycopg2://u:secret@host/db", "postgresql+psycopg2://u:secret@host/db?sslmode=disable&connect_timeout=10", "postgresql+psycopg2://u:secret@localhost/db?sslmode=require&connect_timeout=abc"])
def test_invalid_target_rejected_without_credentials_in_error(url):
    from scripts.migrate_sqlite_to_postgres import validate_target, MigrationError
    with pytest.raises(MigrationError) as exc:
        validate_target(url)
    assert "secret" not in str(exc.value)


def test_loopback_disable_is_allowed_for_local_rehearsal():
    # Disposable local Postgres has no TLS; a loopback-only target may opt out.
    # Any remote host must still carry sslmode=require or stronger.
    from scripts.migrate_sqlite_to_postgres import validate_target
    url = validate_target("postgresql+psycopg2://u@127.0.0.1:5432/db?sslmode=disable&connect_timeout=10")
    assert url.host == "127.0.0.1"


def test_loopback_disable_rejects_destination_overrides():
    # Extra libpq parameters (hostaddr, options) can redirect the connection
    # away from the host in the URL; the loopback exemption must fail closed.
    from scripts.migrate_sqlite_to_postgres import validate_target, MigrationError
    for url in (
        "postgresql+psycopg2://u@127.0.0.1/db?sslmode=disable&connect_timeout=10&hostaddr=203.0.113.9",
        "postgresql+psycopg2://u@localhost/db?sslmode=disable&connect_timeout=10&options=-c%20search_path%3Dpublic",
    ):
        with pytest.raises(MigrationError):
            validate_target(url)


def test_boolean_domain_outside_0_1_fails_closed(tmp_path):
    # SQLite stores booleans as integers; a stored 2 would be silently coerced
    # to True by the typed read, hiding a data change from digest verification.
    from scripts.migrate_sqlite_to_postgres import source_snapshot, inventory, MigrationError
    path = source_database(tmp_path)
    import sqlite3
    raw = sqlite3.connect(path)
    raw.execute("UPDATE users SET is_synthetic=2")
    raw.commit()
    raw.close()
    with source_snapshot(path) as conn, pytest.raises(MigrationError, match="boolean"):
        inventory(conn)


def test_table_digest_is_order_independent():
    # Row order comes from each database's own PK collation; the digest must
    # not depend on it (webauthn_challenges has a mixed-case String PK).
    from datetime import datetime
    from scripts.migrate_sqlite_to_postgres import table_digest
    from app.db import Base
    from app.models import User
    t = Base.metadata.tables["users"]
    rows = [
        {"id": 1, "email": "a@x.dev", "password_hash": None, "is_admin": False,
         "is_synthetic": False, "created_at": datetime(2026, 1, 1)},
        {"id": 2, "email": "B@x.dev", "password_hash": "h", "is_admin": True,
         "is_synthetic": True, "created_at": datetime(2026, 1, 2)},
    ]
    assert table_digest(rows, t) == table_digest(list(reversed(rows)), t)


def test_cli_reports_sanitized_failure_on_broken_app_env():
    # A malformed app .env must surface as the sanitized one-liner, never a
    # traceback that could echo configuration values.
    import os
    import subprocess
    import sys
    env = {**os.environ, "JWT_EXPIRE_MINUTES": "not-an-int", "DATABASE_URL": "sqlite://"}
    r = subprocess.run(
        [sys.executable, "-m", "scripts.migrate_sqlite_to_postgres"],
        capture_output=True, text=True, env=env, timeout=120,
    )
    assert r.returncode == 1
    assert "Migration stopped" in r.stdout
    assert "Traceback" not in r.stderr


def test_default_cli_never_builds_target(tmp_path, monkeypatch, capsys):
    from scripts import migrate_sqlite_to_postgres as migration
    path = source_database(tmp_path)
    monkeypatch.setattr(migration, "load_config", lambda: {"SOURCE_SQLITE_PATH": str(path), "SUPABASE_DATABASE_URL": "not-a-url"})
    monkeypatch.setattr(migration, "create_engine", lambda *a, **k: pytest.fail("target engine built"))
    assert migration.main([]) == 0
    assert "Dry run" in capsys.readouterr().out
