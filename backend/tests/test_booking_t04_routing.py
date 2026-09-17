"""T04 acceptance: chat routes self/other/ambiguous through passenger_ref."""

EMAIL = "asha@examplemail.com"
LOGIN = {"email": EMAIL, "password": "s3cretpw!"}
PROFILE = {
    "email": EMAIL,
    "password": "s3cretpw!",
    "name": "Asha R",
    "age": 21,
    "gender": "female",
    "phone": "9876543210",
}


def _headers(client) -> dict:
    client.post("/api/auth/register", json=PROFILE)
    token = client.post("/api/auth/login", json=LOGIN).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_chat_reports_passenger_ref_self(client):
    headers = _headers(client)
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": "t04-self", "message": "Book a ticket for me to Chennai"},
        headers=headers,
    ).json()
    assert reply["slots"].get("passenger_ref") == "self"


def test_chat_reports_passenger_ref_other(client):
    headers = _headers(client)
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": "t04-other", "message": "Book a ticket for my mother"},
        headers=headers,
    ).json()
    assert reply["slots"].get("passenger_ref") == "other"


def test_chat_reports_passenger_ref_ambiguous(client):
    headers = _headers(client)
    reply = client.post(
        "/api/booking/chat",
        json={"session_id": "t04-amb", "message": "Book two tickets"},
        headers=headers,
    ).json()
    assert reply["slots"].get("passenger_ref") == "ambiguous"
