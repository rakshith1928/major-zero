from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import create_access_token, get_current_user
from app.db import get_db
from app.models import PasskeyCredential, User
from app.schemas import TokenResponse
from app.services import vault, webauthn_service

router = APIRouter(prefix="/api/auth/passkeys", tags=["passkeys"])

# Kept module-level (not in models.py) so PasskeyCredential stays self-describing:
# PasskeyCredential.public_key stores the full AttestedCredentialData as hex
# (credential id + COSE public key), not just the key.


class RegisterCompleteRequest(BaseModel):
    challenge_token: str
    id: str
    rawId: str
    type: str
    response: dict


class LoginOptionsRequest(BaseModel):
    email: EmailStr


class LoginCompleteRequest(BaseModel):
    email: EmailStr
    challenge_token: str
    id: str
    rawId: str
    type: str
    response: dict


@router.get("/register/options")
def register_options(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    options = webauthn_service.registration_options(user, db)
    db.commit()  # persist the challenge for the follow-up /register call
    return options


@router.post("/register", status_code=201)
def register_complete(payload: RegisterCompleteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        registered = webauthn_service.complete_registration(
            db, payload.challenge_token, payload.model_dump()
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    db.add(
        PasskeyCredential(
            user_id=user.id,
            credential_id=registered.credential_id.hex(),
            public_key=registered.attested_data.hex(),
            sign_count=0,
            transports="internal",
        )
    )
    db.commit()
    return {"ok": True}


@router.post("/login/options")
def login_options(payload: LoginOptionsRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=payload.email).one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown email")
    credentials = db.query(PasskeyCredential).filter_by(user_id=user.id).all()
    if not credentials:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no passkeys registered")
    options = webauthn_service.authentication_options(credentials, db)
    db.commit()  # persist the challenge for the follow-up /login call
    return options


@router.post("/login", response_model=TokenResponse)
def login_complete(payload: LoginCompleteRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=payload.email).one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid assertion")
    credentials = db.query(PasskeyCredential).filter_by(user_id=user.id).all()
    stored = [webauthn_service.stored_from_db(c) for c in credentials]
    try:
        verified = webauthn_service.complete_authentication(
            db, payload.challenge_token, payload.model_dump(), stored
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))
    matched = next(
        (c for c in credentials if c.credential_id == verified.credential_id), None
    )
    if matched is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "credential mismatch")
    matched.sign_count = verified.new_sign_count
    db.commit()
    _ = vault  # vault access is audited at booking time; login itself stays light
    return TokenResponse(access_token=create_access_token(user.id))
