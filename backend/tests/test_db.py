"""The DB layer must build a Postgres (Supabase) engine without SQLite-only options."""

from app import db


def test_build_engine_keys_options_on_database_url(monkeypatch):
    calls = {}

    def fake_create_engine(url, **kwargs):
        calls["url"] = url
        calls["kwargs"] = kwargs
        return "engine-sentinel"

    monkeypatch.setattr(db, "create_engine", fake_create_engine)

    postgres = db.build_engine(
        "postgresql+psycopg2://postgres:pw@db.proj.supabase.co:5432/postgres"
    )
    assert postgres == "engine-sentinel"
    assert calls["url"].startswith("postgresql+psycopg2://")
    # psycopg2 must receive no SQLite-specific kwargs and no StaticPool.
    assert calls["kwargs"] == {"connect_args": {}, "pool_pre_ping": True}

    sqlite_file = db.build_engine("sqlite:///D:/tmp/zerobus.db")
    assert sqlite_file == "engine-sentinel"
    assert calls["kwargs"]["connect_args"] == {"check_same_thread": False}
    assert "poolclass" not in calls["kwargs"]

    sqlite_memory = db.build_engine("sqlite://")
    assert sqlite_memory == "engine-sentinel"
    assert calls["kwargs"]["poolclass"] is db.StaticPool
