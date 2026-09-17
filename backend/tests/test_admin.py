"""T11 — admin dashboard API: aggregates + warning analytics, admin-only."""

ADMIN = {
    "email": "admin@zerobusmail.com",
    "password": "adminpw123",
    "name": "Admin",
    "age": 30,
    "gender": "male",
    "phone": "9000000000",
}
USER = {
    "email": "asha@examplemail.com",
    "password": "s3cretpw!",
    "name": "Asha R",
    "age": 21,
    "gender": "female",
    "phone": "9876543210",
}


def _token(client, profile) -> str:
    client.post("/api/auth/register", json=profile)
    return client.post(
        "/api/auth/login",
        json={"email": profile["email"], "password": profile["password"]},
    ).json()["access_token"]


def test_admin_overview_requires_admin(client, session):
    user_headers = {"Authorization": f"Bearer {_token(client, USER)}"}
    assert client.get("/api/admin/overview", headers=user_headers).status_code == 403

    admin_headers = {"Authorization": f"Bearer {_token(client, ADMIN)}"}
    body = client.get("/api/admin/overview", headers=admin_headers).json()
    assert "totals" in body
    assert "warnings" in body
    assert "demand" in body


def test_admin_overview_counts_reflect_activity(client, session):
    from app.seed.buses import seed_buses

    admin_headers = {"Authorization": f"Bearer {_token(client, ADMIN)}"}
    user_headers = {"Authorization": f"Bearer {_token(client, USER)}"}
    seed_buses(session)
    before = client.get("/api/admin/overview", headers=admin_headers).json()["totals"]
    client.post(
        "/api/booking/chat",
        json={"session_id": "adm-1", "message": "book a bus to Chennai"},
        headers=user_headers,
    )
    after = client.get("/api/admin/overview", headers=admin_headers).json()["totals"]
    assert after["chat_messages"] > before["chat_messages"]


def test_anonymous_admin_access_is_unauthorized(client):
    assert client.get("/api/admin/overview").status_code in (401, 403)
