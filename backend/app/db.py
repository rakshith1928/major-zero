from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings


def build_engine(url: str):
    """Engine factory shared by app startup and the migration script.

    SQLite needs check_same_thread=False because FastAPI/pytest use several
    threads; a pure in-memory database additionally needs StaticPool so all
    connections share it. Postgres drivers (Supabase) reject SQLite-specific
    kwargs, and hosted poolers drop idle connections — hence pre-ping.
    """
    if url == "sqlite://":
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, connect_args={}, pool_pre_ping=True)


engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
