"""T12 — notification fan-out (ADR-014).

Payment success writes an in-app Notification row always, then attempts the
confirmation email best-effort: SMTP failure is logged, never raised, so a
mail outage can never fail a booking (graceful degradation).
"""

import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Notification

log = logging.getLogger("zerobus.notifications")


def notify(db: Session, user_id: int, type: str, title: str, body: str) -> Notification:
    row = Notification(user_id=user_id, type=type, title=title, body=body)
    db.add(row)
    db.flush()
    return row


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not settings.smtp_host or not settings.smtp_user:
        log.info("SMTP not configured; skipping email to %s", to_email)
        return False
    try:
        message = EmailMessage()
        message["From"] = settings.smtp_user
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password or "")
            smtp.send_message(message)
        return True
    except Exception as exc:  # never break the booking flow for mail
        log.warning("email to %s failed: %s", to_email, exc)
        return False


def payment_succeeded(
    db: Session, user, booking, ticket_code: str, ticket_link: str = ""
) -> None:
    body = (
        f"Booking {booking.booking_ref} confirmed. "
        f"Ticket code: {ticket_code}. "
        f"Travel date: {booking.travel_date.isoformat()}. Fare: Rs.{booking.fare}."
    )
    if ticket_link:
        body += f" View your ticket: {ticket_link}"
    notify(db, user.id, "PAYMENT_SUCCESS", "Payment successful — ticket booked", body)
    send_email(
        to_email=user.email,
        subject=f"ZeroBus ticket {booking.booking_ref}",
        body=body,
    )


def trip_reminder(db: Session, user, booking, ticket_code: str) -> None:
    """Upcoming-trip reminder (TRIP_REMINDER) for tomorrow's bookings."""
    body = (
        f"Reminder: your bus {booking.booking_ref} travels tomorrow "
        f"({booking.travel_date.isoformat()}). Ticket code: {ticket_code}. "
        f"Boarding point: {booking.boarding_point}."
    )
    notify(db, user.id, "TRIP_REMINDER", "Your trip is tomorrow", body)
    send_email(
        to_email=user.email,
        subject=f"Reminder: ZeroBus trip {booking.booking_ref} tomorrow",
        body=body,
    )


def send_due_reminders(db: Session, today=None) -> int:
    """Fan-out reminders for all PAID bookings travelling tomorrow."""
    from datetime import date, timedelta

    from app.models import Booking

    today = today or date.today()
    tomorrow = today + timedelta(days=1)
    sent = 0
    for booking in (
        db.query(Booking)
        .filter(Booking.status == "PAID", Booking.travel_date == tomorrow)
        .all()
    ):
        from app.models import Ticket, User

        ticket = db.query(Ticket).filter_by(booking_id=booking.id).first()
        passenger = db.get(User, booking.user_id)
        if passenger is None:
            continue
        already = (
            db.query(Notification)
            .filter_by(user_id=passenger.id, type="TRIP_REMINDER")
            .filter(Notification.body.contains(booking.booking_ref))
            .first()
        )
        if already:
            continue
        trip_reminder(
            db, passenger, booking, ticket.code if ticket else "see /api/tickets"
        )
        sent += 1
    db.commit()
    return sent
