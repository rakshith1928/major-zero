"""Settings must tolerate operational env vars it does not model (ADR-011).

HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE are required in every run environment
and are consumed by the Hugging Face libraries, not by Settings. They appear
both as process env vars and in backend/.env — neither source may crash
configuration loading.
"""

from app.config import Settings


def test_env_file_unknown_keys_are_ignored(tmp_path, monkeypatch):
    # A real HF_HOME process var would outrank the dotenv file and mask it.
    monkeypatch.delenv("HF_HOME", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "HF_HUB_OFFLINE=1\nTRANSFORMERS_OFFLINE=1\nHF_HOME=D:\\models\n",
        encoding="utf-8",
    )
    s = Settings(_env_file=env_file)
    assert s.jwt_secret  # normal fields still load
    assert s.hf_home == r"D:\models"


def test_process_env_offline_flags_do_not_crash_settings(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    s = Settings()
    assert s.database_url  # default (or .env) value present
