"""WebAuthn (passkey) server ceremonies, built on fido2 (ADR-002).

Wire contract (matches @simplewebauthn/browser on the frontend):
- options endpoints return {"publicKey": {...base64url...}, "challenge_token": "..."}
- complete endpoints accept that same JSON shape plus the challenge_token.
- challenge state lives only for one options -> complete round trip.
"""

import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from fido2.features import webauthn_json_mapping
from fido2.server import Fido2Server
from fido2.utils import websafe_encode
from fido2.webauthn import (
    AttestedCredentialData,
    AuthenticationResponse,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity,
    RegistrationResponse,
)

from app.config import settings

webauthn_json_mapping.enabled = True

CHALLENGE_TTL_SECONDS = 300


def _save_challenge(db, token: str, purpose: str, state: dict, user_id: int | None) -> None:
    from datetime import datetime, timedelta

    from app.models import WebauthnChallenge

    challenge = state["challenge"]
    db.add(
        WebauthnChallenge(
            token=token,
            purpose=purpose,
            challenge_hex=(
                "b64:" + challenge if isinstance(challenge, str) else challenge.hex()
            ),
            user_verification=state.get("user_verification", "preferred"),
            user_id=user_id,
            created_at=datetime.utcnow(),
        )
    )
    # Opportunistic cleanup: drop expired challenges in the same write.
    db.query(WebauthnChallenge).filter(
        WebauthnChallenge.created_at
        < datetime.utcnow() - timedelta(seconds=CHALLENGE_TTL_SECONDS)
    ).delete()


def _pop_challenge(db, token: str, purpose: str) -> dict | None:
    from datetime import datetime, timedelta

    from app.models import WebauthnChallenge

    row = (
        db.query(WebauthnChallenge)
        .filter_by(token=token, purpose=purpose)
        .one_or_none()
    )
    if row is None:
        return None
    db.delete(row)
    db.flush()
    if row.created_at < datetime.utcnow() - timedelta(seconds=CHALLENGE_TTL_SECONDS):
        return None  # expired: force a fresh ceremony
    if row.challenge_hex.startswith("b64:"):
        challenge = row.challenge_hex[4:]
    else:
        challenge = bytes.fromhex(row.challenge_hex)
    return {"challenge": challenge, "user_verification": row.user_verification}


def to_wire(obj):
    """Convert fido2 option objects to base64url JSON for the browser."""
    if isinstance(obj, bytes):
        return websafe_encode(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Mapping):
        return {key: to_wire(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_wire(value) for value in obj]
    return obj


def _server() -> Fido2Server:
    return Fido2Server(
        PublicKeyCredentialRpEntity(id=settings.webauthn_rp_id, name="ZeroBus"),
        verify_origin=lambda origin: origin == settings.webauthn_origin,
    )


def registration_options(user, db=None) -> dict:
    options, state = _server().register_begin(
        PublicKeyCredentialUserEntity(
            id=str(user.id).encode("utf-8"),
            name=user.email,
            display_name=user.email,
        ),
    )
    token = secrets.token_urlsafe(32)
    if db is not None:
        _save_challenge(db, token, "registration", state, user.id)
    return {
        "publicKey": to_wire(options.public_key),
        "challenge_token": token,
    }


@dataclass
class RegisteredCredential:
    credential_id: bytes
    attested_data: bytes  # full AttestedCredentialData; unpack for id + COSE key


def complete_registration(db, token: str, attestation: dict) -> RegisteredCredential:
    state = _pop_challenge(db, token, "registration")
    if state is None:
        raise ValueError("registration challenge expired or unknown")
    auth_data = _server().register_complete(
        state, RegistrationResponse.from_dict(attestation)
    )
    attested = bytes(auth_data.credential_data)
    if not attested:
        raise ValueError("registration produced no credential")
    credential_id, _rest = AttestedCredentialData.unpack_from(attested)[0], None
    return RegisteredCredential(
        credential_id=credential_id.credential_id, attested_data=attested
    )


def authentication_options(credentials: list, authentication_db=None) -> dict:
    descriptors = [
        PublicKeyCredentialDescriptor(
            id=bytes.fromhex(cred.credential_id), type="public-key"
        )
        for cred in credentials
    ]
    options, state = _server().authenticate_begin(descriptors)
    token = secrets.token_urlsafe(32)
    if authentication_db is not None:
        _save_challenge(authentication_db, token, "authentication", state, None)
    return {"publicKey": to_wire(options.public_key), "challenge_token": token}


@dataclass
class StoredCredential:
    credential_id: bytes
    public_key: object
    sign_count: int


@dataclass
class VerifiedAssertion:
    credential_id: str
    new_sign_count: int


def complete_authentication(
    db, token: str, assertion: dict, stored: list[StoredCredential]
) -> VerifiedAssertion:
    state = _pop_challenge(db, token, "authentication")
    if state is None:
        raise ValueError("authentication challenge expired or unknown")
    # fido2 1.2 returns the MATCHED credential object itself (not a tuple).
    response = AuthenticationResponse.from_dict(assertion)
    matched = _server().authenticate_complete(state, stored, response)
    if matched is None:
        raise ValueError("assertion did not match any credential")
    # Clone detection: the authenticator's counter must move forward.
    new_count = response.response.authenticator_data.counter
    prior = next(
        (c for c in stored if c.credential_id == matched.credential_id), None
    )
    if prior is not None and new_count != 0 and new_count <= prior.sign_count:
        raise ValueError("sign count did not advance; possible cloned authenticator")
    return VerifiedAssertion(
        credential_id=matched.credential_id.hex(),
        new_sign_count=new_count if new_count else prior.sign_count + 1,
    )


def stored_from_db(cred) -> StoredCredential:
    attested, _rest = AttestedCredentialData.unpack_from(
        bytes.fromhex(cred.public_key)
    )
    return StoredCredential(
        credential_id=bytes.fromhex(cred.credential_id),
        public_key=attested.public_key,
        sign_count=cred.sign_count,
    )
