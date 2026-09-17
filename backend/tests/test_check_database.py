from scripts import check_database


def test_missing_target_fails_without_network(monkeypatch, capsys):
    monkeypatch.setattr(check_database, "load_config", lambda: {})
    assert check_database.main([]) == 1
    assert "configuration invalid" in capsys.readouterr().out


def test_default_only_validates_config(monkeypatch, capsys):
    monkeypatch.setattr(check_database, "load_config", lambda: {"SUPABASE_DATABASE_URL": "postgresql+psycopg2://u:private-password@host/db?sslmode=require&connect_timeout=10"})
    monkeypatch.setattr(check_database, "create_engine", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    assert check_database.main([]) == 0
    output = capsys.readouterr().out
    assert "no connection" in output
    assert "private-password" not in output
