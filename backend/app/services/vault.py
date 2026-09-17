"""Encrypted passenger vault (ADR-002/ADR-006).

Each user's vault entries are encrypted with a key derived from the server
master secret and the user id, so one leaked key does not open every profile.
"""

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _key_for_user(user_id: int) -> bytes:
    digest = hashlib.sha256(
        f"{settings.fernet_master}:{user_id}".encode("utf-8")
    ).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_for_user(user_id: int, details: dict) -> str:
    fernet = Fernet(_key_for_user(user_id))
    return fernet.encrypt(json.dumps(details).encode("utf-8")).decode("ascii")


def decrypt_for_user(
    user_id: int,
    token: str,
    db=None,
    profile_id: int | None = None,
    endpoint: str = "",
) -> dict:
    fernet = Fernet(_key_for_user(user_id))
    try:
        details = json.loads(fernet.decrypt(token.encode("ascii")))
    except (InvalidToken, ValueError) as exc:
        raise ValueError("vault entry cannot be decrypted for this user") from exc
    if db is not None:
        from app.models import VaultAuditLog

        db.add(
            VaultAuditLog(
                user_id=user_id, profile_id=profile_id, endpoint=endpoint
            )
        )
        db.flush()
    return details
