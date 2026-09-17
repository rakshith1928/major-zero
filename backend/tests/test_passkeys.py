"""Passkey ceremony through the HTTP seam.

The test emulates the browser faithfully: the server emits base64url JSON,
the browser decodes binary fields back to ArrayBuffers before calling the
authenticator (here: SoftWebauthnDevice), and the authenticator's raw output
is re-encoded to base64url JSON for the complete call.
"""

from fido2.utils import websafe_decode, websafe_encode
from soft_webauthn import SoftWebauthnDevice

EMAIL = "asha@examplemail.com"
ORIGIN = "https://testserver"


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _registered_user_token(client) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "email": EMAIL,
            "password": "s3cretpw!",
            "name": "Asha R",
            "age": 21,
            "gender": "female",
            "phone": "9876543210",
        },
    )
    return response.json()["access_token"]


def _decode_binary(node):
    """Browser step: base64url JSON back to binary (bytes) before authenticator.

    Only values that were actually base64url-encoded *bytes* on the server are
    decoded back. Plain-text strings (names, ids, types) must pass through
    untouched: decoding "public-key" as base64url would mangle it.
    """
    if isinstance(node, dict):
        return {k: _decode_binary(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_decode_binary(v) for v in node]
    return node


def _decode_field(value: str) -> bytes:
    return websafe_decode(value)


def _encode_binary(node):
    """Authenticator output back to base64url JSON for the HTTP complete call.

    SoftWebauthnDevice pre-encodes id/rawId itself; re-encoding them would
    corrupt the credential id, so str leaves are passed through untouched.
    """
    if isinstance(node, bytes):
        return websafe_encode(node)
    if isinstance(node, dict):
        return {k: _encode_binary(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_encode_binary(v) for v in node]
    return node


def _reencode_id(value):
    """Normalize an id the test device hands back.

    SoftWebauthnDevice already returns id/rawId as base64url *bytes*.
    Double-encoding them (treating them as raw bytes again) corrupts the
    credential id — the registration-login mismatch this helper fixes.
    """
    if isinstance(value, bytes):
        try:
            value.decode("ascii")
            websafe_decode(value.decode("ascii"))
            return value.decode("ascii")
        except Exception:
            return websafe_encode(value)
    return value


def _encode_attestation(attestation: dict) -> dict:
    encoded = _encode_binary(attestation)
    encoded["id"] = _reencode_id(attestation["id"])
    encoded["rawId"] = _reencode_id(attestation["rawId"])
    return encoded


def _encode_assertion(assertion: dict) -> dict:
    encoded = _encode_binary(assertion)
    encoded["id"] = _reencode_id(assertion["id"])
    encoded["rawId"] = _reencode_id(assertion["rawId"])
    return encoded


def _browser_registration_payload(options_response: dict) -> dict:
    """Emulate what a real browser does with the registration options response:

    base64url-decode exactly the binary fields (challenge + user id) into
    ArrayBuffers; leave every human-readable string untouched.
    """
    options = dict(options_response)
    pk = dict(options["publicKey"])
    pk["challenge"] = _decode_field(pk["challenge"])
    user = dict(pk["user"])
    user["id"] = _decode_field(user["id"])
    pk["user"] = user
    options["publicKey"] = pk
    return options


def _browser_assertion_payload(options_response: dict) -> dict:
    options = dict(options_response)
    pk = dict(options["publicKey"])
    pk["challenge"] = _decode_field(pk["challenge"])
    if pk.get("allowCredentials"):
        pk["allowCredentials"] = [
            {**cred, "id": _decode_field(cred["id"])} for cred in pk["allowCredentials"]
        ]
    options["publicKey"] = pk
    return options


def _register_device(client, token, origin=ORIGIN):
    options = client.get(
        "/api/auth/passkeys/register/options", headers=_bearer(token)
    ).json()
    device = SoftWebauthnDevice()
    attestation = device.create(_browser_registration_payload(options), origin)
    attested = _encode_attestation(attestation)
    attested["challenge_token"] = options["challenge_token"]
    return device, attested


def test_passkey_can_be_registered_and_used_for_passwordless_login(client):
    token = _registered_user_token(client)
    device, attestation = _register_device(client, token)
    assert (
        client.post(
            "/api/auth/passkeys/register", json=attestation, headers=_bearer(token)
        ).status_code
        == 201
    )

    options = client.post(
        "/api/auth/passkeys/login/options", json={"email": EMAIL}
    ).json()
    assertion = device.get(_browser_assertion_payload(options), ORIGIN)
    assertion = _encode_assertion(assertion)
    assertion.update({"email": EMAIL, "challenge_token": options["challenge_token"]})
    response = client.post("/api/auth/passkeys/login", json=assertion)
    assert response.status_code == 200
    new_token = response.json()["access_token"]
    me = client.get("/api/auth/me", headers=_bearer(new_token))
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


def test_passkey_rejects_assertion_from_unexpected_origin(client):
    token = _registered_user_token(client)
    device, attestation = _register_device(client, token)
    client.post(
        "/api/auth/passkeys/register", json=attestation, headers=_bearer(token)
    )

    options = client.post(
        "/api/auth/passkeys/login/options", json={"email": EMAIL}
    ).json()
    assertion = device.get(
        _browser_assertion_payload(options),
        "https://evil.example.com",
    )
    assertion = _encode_assertion(assertion)
    assertion.update({"email": EMAIL, "challenge_token": options["challenge_token"]})
    response = client.post("/api/auth/passkeys/login", json=assertion)
    assert response.status_code in (400, 401)


def test_passkey_login_options_for_unknown_email_is_not_found(client):
    response = client.post(
        "/api/auth/passkeys/login/options", json={"email": "ghost@examplemail.com"}
    )
    assert response.status_code == 404
