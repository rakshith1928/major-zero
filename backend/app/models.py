import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _short_ref() -> str:
    return uuid.uuid4().hex[:10].upper()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PasskeyCredential(Base):
    __tablename__ = "passkey_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    credential_id: Mapped[str] = mapped_column(String(512), unique=True)
    public_key: Mapped[str] = mapped_column(Text)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PassengerProfile(Base):
    """Encrypted passenger vault entry (own profile or a consented other passenger)."""

    __tablename__ = "passenger_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    is_self: Mapped[bool] = mapped_column(Boolean, default=False)
    label: Mapped[str] = mapped_column(String(100), default="Self")
    # Fernet-encrypted JSON: {name, age, gender, phone}
    data_encrypted: Mapped[str] = mapped_column(Text)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Bus(Base):
    """A daily departure template (runs every day of the 30-day window)."""

    __tablename__ = "buses"

    id: Mapped[int] = mapped_column(primary_key=True)
    operator: Mapped[str] = mapped_column(String(100))
    bus_type: Mapped[str] = mapped_column(String(32))  # AC_SLEEPER / AC_SEMI_SLEEPER / NON_AC_SEATER
    origin: Mapped[str] = mapped_column(String(100), index=True)
    destination: Mapped[str] = mapped_column(String(100), index=True)
    departure_time: Mapped[time] = mapped_column(Time)
    arrival_time: Mapped[time] = mapped_column(Time)
    arrival_day_offset: Mapped[int] = mapped_column(Integer, default=0)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    base_fare: Mapped[int] = mapped_column(Integer)
    total_seats: Mapped[int] = mapped_column(Integer)


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (Index("ix_bookings_bus_date", "bus_id", "travel_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_ref: Mapped[str] = mapped_column(String(16), unique=True, default=_short_ref)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id"))
    travel_date: Mapped[date] = mapped_column(Date)
    passenger_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("passenger_profiles.id"), nullable=True
    )
    # Snapshot of the details actually used, encrypted (may be a third party).
    passenger_snapshot_encrypted: Mapped[str] = mapped_column(Text)
    boarding_point: Mapped[str] = mapped_column(String(100))
    fare: Mapped[int] = mapped_column(Integer)
    deadline_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="PENDING_PAYMENT")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    # T13: fields the user typed manually (frontend-reported); 0 = full zero-form.
    manual_fields: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    bus: Mapped["Bus"] = relationship()


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, default=_short_ref)
    qr_payload: Mapped[str] = mapped_column(Text)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    order_id: Mapped[str] = mapped_column(String(100))
    payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    signature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="CREATED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WarningLog(Base):
    __tablename__ = "warnings_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    detector: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(24))  # FIRED / ACCEPTED / OVERRIDDEN
    detail: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_user_session", "user_id", "session_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MetricRow(Base):
    """Persisted per-task study metric (T13: every booking leaves a row)."""

    __tablename__ = "metric_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(64))
    task: Mapped[str] = mapped_column(String(100))
    booking_ref: Mapped[str] = mapped_column(String(16))
    booking_seconds: Mapped[int] = mapped_column(Integer, default=0)
    manual_fields: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VaultAuditLog(Base):
    """Every vault decryption, for the privacy story (T02 acceptance)."""

    __tablename__ = "vault_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("passenger_profiles.id"), nullable=True
    )
    endpoint: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PendingPassenger(Base):
    """Chat-captured passenger awaiting the consent answer (T05)."""

    __tablename__ = "pending_passengers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    details_encrypted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MetricStart(Base):
    """Open study-task stopwatch (T13); closed when /finish pops it."""

    __tablename__ = "metric_starts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(64))
    task: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WebauthnChallenge(Base):
    """Live WebAuthn challenge state; single options -> complete round trip."""

    __tablename__ = "webauthn_challenges"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(16))  # registration / authentication
    challenge_hex: Mapped[str] = mapped_column(String(128))
    user_verification: Mapped[str] = mapped_column(String(32), default="preferred")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
