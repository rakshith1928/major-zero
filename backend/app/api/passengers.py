"""T05 — other-passenger capture, opt-in memory, saved profiles (ADR-006)."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import ChatMessage, PassengerProfile, User
from app.services import vault

router = APIRouter(tags=["passengers"])

PENDING_TTL_SECONDS = 600


def _save_pending(db: Session, user_id: int, session_id: str, details: dict) -> None:
    from datetime import datetime, timedelta

    from app.models import PendingPassenger

    db.query(PendingPassenger).filter_by(user_id=user_id, session_id=session_id).delete()
    db.add(
        PendingPassenger(
            user_id=user_id,
            session_id=session_id,
            details_encrypted=vault.encrypt_for_user(user_id, details),
            created_at=datetime.utcnow(),
        )
    )
    # Opportunistic cleanup of stale pending captures.
    db.query(PendingPassenger).filter(
        PendingPassenger.created_at
        < datetime.utcnow() - timedelta(seconds=PENDING_TTL_SECONDS)
    ).delete()


def _pop_pending(db: Session, user_id: int, session_id: str) -> dict | None:
    from datetime import datetime, timedelta

    from app.models import PendingPassenger

    row = (
        db.query(PendingPassenger)
        .filter_by(user_id=user_id, session_id=session_id)
        .one_or_none()
    )
    if row is None:
        return None
    db.delete(row)
    db.flush()
    if row.created_at < datetime.utcnow() - timedelta(seconds=PENDING_TTL_SECONDS):
        return None
    return vault.decrypt_for_user(
        user_id, row.details_encrypted, db, None, "pending-passenger-pop"
    )


class CaptureRequest(BaseModel):
    session_id: str
    name: str = Field(min_length=1)
    age: int = Field(ge=1, le=120)
    gender: str
    phone: str = Field(min_length=10, max_length=15)


class ConsentRequest(BaseModel):
    session_id: str
    remember: bool
    label: str = "Saved passenger"


def _mask(phone: str) -> str:
    return ("*" * max(0, len(phone) - 4)) + phone[-4:]


@router.post("/api/booking/passenger/capture")
def capture(
    req: CaptureRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    details = {"name": req.name, "age": req.age, "gender": req.gender, "phone": req.phone}
    _save_pending(db, user.id, req.session_id, details)
    db.add(
        ChatMessage(
            user_id=user.id,
            session_id=req.session_id,
            role="assistant",
            content=(
                f"Got it — {req.name}, {req.age}. "
                "Should I remember these details for next time?"
            ),
            meta=json.dumps({"captured": True}),
        )
    )
    db.commit()
    return {"passenger": {**details, "phone": _mask(req.phone)}, "needs_consent": True}


@router.post("/api/booking/passenger/consent")
def consent(
    req: ConsentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    details = _pop_pending(db, user.id, req.session_id)
    if details is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "nothing to remember")
    if not req.remember:
        return {"remembered": False}
    profile = PassengerProfile(
        owner_user_id=user.id,
        is_self=False,
        label=req.label,
        data_encrypted=vault.encrypt_for_user(user.id, details),
        consent_given=True,
    )
    db.add(profile)
    db.commit()
    return {"remembered": True, "profile_id": profile.id}


@router.get("/api/passengers")
def list_passengers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profiles = (
        db.query(PassengerProfile)
        .filter_by(owner_user_id=user.id, is_self=False)
        .order_by(PassengerProfile.id)
        .all()
    )
    out = []
    for profile in profiles:
        details = vault.decrypt_for_user(user.id, profile.data_encrypted, db, profile.id, "GET /api/passengers")
        out.append(
            {
                "id": profile.id,
                "label": profile.label,
                "name": details.get("name"),
                "age": details.get("age"),
                "gender": details.get("gender"),
                "phone": _mask(details.get("phone", "")),
            }
        )
    return {"passengers": out}


@router.delete("/api/passengers/{profile_id}", status_code=204)
def delete_passenger(
    profile_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(PassengerProfile)
        .filter_by(id=profile_id, owner_user_id=user.id, is_self=False)
        .one_or_none()
    )
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown passenger")
    db.delete(profile)
    db.commit()
    return None
