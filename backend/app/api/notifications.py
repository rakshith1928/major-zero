"""T12 — in-app notification inbox."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import Notification, User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def inbox(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Notification)
        .filter_by(user_id=user.id)
        .order_by(Notification.id.desc())
        .all()
    )
    return {
        "notifications": [
            {
                "id": r.id,
                "type": r.type,
                "title": r.title,
                "body": r.body,
                "read": r.read,
            }
            for r in rows
        ]
    }
