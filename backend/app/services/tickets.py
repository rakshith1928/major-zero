"""T07 — signed QR ticket payloads (issue + verify)."""

import base64
import hashlib
import hmac
import json

from app.config import settings


def sign_payload(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(settings.ticket_secret.encode(), body, hashlib.sha256).hexdigest()
    envelope = {"data": payload, "sig": signature}
    return base64.urlsafe_b64encode(
        json.dumps(envelope, separators=(",", ":")).encode()
    ).decode("ascii")


def verify_payload(qr_payload: str) -> dict | None:
    try:
        envelope = json.loads(base64.urlsafe_b64decode(qr_payload.encode()))
        payload, signature = envelope["data"], envelope["sig"]
    except Exception:
        return None
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(settings.ticket_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    return payload
