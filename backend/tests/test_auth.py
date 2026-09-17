REGISTER_PAYLOAD = {
    "email": "asha@examplemail.com",
    "password": "s3cretpw!",
    "name": "Asha R",
    "age": 21,
    "gender": "female",
    "phone": "9876543210",
}


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_user_with_encrypted_self_profile(client, session):
    from app.models import PassengerProfile
    from app.services.vault import decrypt_for_user

    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]

    profile = session.query(PassengerProfile).filter_by(is_self=True).one()
    assert "Asha" not in profile.data_encrypted, "PII must be encrypted at rest"
    details = decrypt_for_user(profile.owner_user_id, profile.data_encrypted)
    assert details["name"] == "Asha R"
    assert details["age"] == 21
    assert details["gender"] == "female"


def test_register_rejects_duplicate_email(client):
    assert client.post("/api/auth/register", json=REGISTER_PAYLOAD).status_code == 201
    assert client.post("/api/auth/register", json=REGISTER_PAYLOAD).status_code == 409


def test_login_with_correct_password_returns_token(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/api/auth/login",
        json={"email": "asha@examplemail.com", "password": "s3cretpw!"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_wrong_password_is_unauthorized(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/api/auth/login",
        json={"email": "asha@examplemail.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_email_for_valid_token(client):
    token = client.post("/api/auth/register", json=REGISTER_PAYLOAD).json()["access_token"]
    response = client.get("/api/auth/me", headers=_bearer(token))
    assert response.status_code == 200
    assert response.json()["email"] == "asha@examplemail.com"


def test_vault_decryption_writes_audit_row(client, session):
    from datetime import date

    from app import models
    from app.db import SessionLocal
    from app.seed.buses import seed_buses

    token = client.post(
        "/api/auth/register",
        json={
            "email": "audit@examplemail.com",
            "password": "s3cretpw!",
            "name": "Audit U",
            "age": 30,
            "gender": "male",
            "phone": "9111111111",
        },
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    with SessionLocal() as db:
        seed_buses(db)
        bus_id = db.query(models.Bus).first().id
    client.post(
        "/api/booking/chat",
        json={"session_id": "audit-1", "message": "book a bus to Chennai for me"},
        headers=headers,
    )
    client.post(
        "/api/booking/select",
        json={
            "session_id": "audit-1",
            "bus_id": bus_id,
            "travel_date": date.today().isoformat(),
            "boarding_point": "Bangalore",
        },
        headers=headers,
    )
    rows = session.query(models.VaultAuditLog).all()
    assert rows, "expected a vault audit row per decryption"
    assert all(r.endpoint for r in rows)
