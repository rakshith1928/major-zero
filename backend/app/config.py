from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # SQLite remains the offline fallback; hosted deployments use Supabase Postgres.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'zerobus.db'}"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12

    # ADR-011: the ONLY Hugging Face download ever; cache lives on D:.
    hf_home: str = r"D:\New folder (2)\models\huggingface"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ADR-002: WebAuthn relying-party identity (server origin in the demo).
    webauthn_rp_id: str = "localhost"
    webauthn_origin: str = "http://localhost:5173"

    # Vault master secret (per-user keys are derived from it).
    fernet_master: str = "dev-master-secret-change-me"

    # T07: HMAC secret signing QR ticket payloads.
    ticket_secret: str = "dev-ticket-secret-change-me"

    # Admin allowlist (comma-separated emails). Empty = nobody can self-elevate.
    admin_emails: str = ""

    # Browser origins allowed to call the API (CORS).
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_emails_list(self) -> list:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]

    # External services (test/placeholder keys until real ones are configured).
    gemini_api_key: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
