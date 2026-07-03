def test_register_creates_user(client):
    res = client.post("/auth/register", json={
        "org_name": "Acme Inc",
        "email": "user@acme.com",
        "password": "securepass123",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "user@acme.com"
    assert "hashed_password" not in body  # never leak the hash


def test_register_duplicate_email_fails(client):
    payload = {"org_name": "Acme Inc", "email": "dup@acme.com", "password": "securepass123"}
    client.post("/auth/register", json=payload)
    res = client.post("/auth/register", json=payload)
    assert res.status_code == 400


def test_login_with_correct_credentials_returns_token(client):
    client.post("/auth/register", json={
        "org_name": "Acme", "email": "login@acme.com", "password": "securepass123",
    })
    res = client.post("/auth/login", json={"email": "login@acme.com", "password": "securepass123"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_with_wrong_password_fails(client):
    client.post("/auth/register", json={
        "org_name": "Acme", "email": "wrongpw@acme.com", "password": "securepass123",
    })
    res = client.post("/auth/login", json={"email": "wrongpw@acme.com", "password": "nope"})
    assert res.status_code == 401


def test_protected_route_requires_token(client):
    res = client.get("/projects")
    assert res.status_code == 401