"""T13 — study metrics harness: task timing + manual-field counts."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import Booking, ChatMessage, MetricRow, MetricStart, User

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


class StartRequest(BaseModel):
    session_id: str
    task: str


class FinishRequest(BaseModel):
    session_id: str
    booking_ref: str
    success: bool


@router.post("/start")
def start(req: StartRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.add(
        MetricStart(
            user_id=user.id, session_id=req.session_id, task=req.task
        )
    )
    db.commit()
    return {"ok": True}


@router.post("/finish")
def finish(
    req: FinishRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    started = (
        db.query(MetricStart)
        .filter_by(user_id=user.id, session_id=req.session_id)
        .order_by(MetricStart.id.desc())
        .first()
    )
    if started is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "no matching start")
    seconds = round((datetime.utcnow() - started.started_at).total_seconds(), 2)
    task = started.task
    db.delete(started)
    db.flush()
    booking = (
        db.query(Booking)
        .filter_by(booking_ref=req.booking_ref, user_id=user.id)
        .one_or_none()
    )
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown booking")

    manual_fields = sum(
        1
        for row in db.query(ChatMessage)
        .filter_by(user_id=user.id, session_id=req.session_id, role="user")
        .all()
        if any(
            token in row.content.lower()
            for token in ["my name is", "my age", "my phone", "i am ", "years old"]
        )
    )
    manual_fields += int(getattr(booking, "manual_fields", 0) or 0)
    db.add(
        MetricRow(
            user_id=user.id,
            session_id=req.session_id,
            task=task,
            booking_ref=req.booking_ref,
            booking_seconds=int(seconds),
            manual_fields=manual_fields,
            success=req.success,
        )
    )
    db.commit()
    return {
        "task": task,
        "booking_seconds": seconds,
        "manual_fields": manual_fields,
        "success": req.success,
        "booking_ref": req.booking_ref,
    }
