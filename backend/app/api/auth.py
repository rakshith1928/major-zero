from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import create_access_token, get_current_user
from app.db import get_db
from app.models import PassengerProfile, User
from app.schemas import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.services import vault

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _self_profile_for(db: Session, user_id: int) -> PassengerProfile | None:
    return (
        db.query(PassengerProfile)
        .filter_by(owner_user_id=user_id, is_self=True)
        .one_or_none()
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=payload.email).one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    from app.services.passwords import hash_password

    from app.config import settings

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    if payload.email in settings.admin_emails_list:
        user.is_admin = True
    db.add(user)
    db.flush()
    db.add(
        PassengerProfile(
            owner_user_id=user.id,
            is_self=True,
            label="Self",
            data_encrypted=vault.encrypt_for_user(
                user.id,
                {
                    "name": payload.name,
                    "age": payload.age,
                    "gender": payload.gender,
                    "phone": payload.phone,
                },
            ),
        )
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    from app.services.passwords import verify_password

    user = db.query(User).filter_by(email=payload.email).one_or_none()
    if user is None or not user.password_hash or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email, is_admin=user.is_admin)
