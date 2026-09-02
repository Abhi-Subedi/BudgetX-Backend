from tests.conftest import register_and_login


def test_register_login_refresh_me(client):
    auth = register_and_login(client, currency="USD")
    assert auth["user"]["email"] == "asha@example.com"

    me = client.get("/api/users/me", headers=auth["headers"])
    assert me.status_code == 200
    assert me.json()["name"] == "Asha Rai"

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": auth["refresh"]})
    assert refreshed.status_code == 200
    new_access = refreshed.json()["tokens"]["access_token"]
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {new_access}"}).status_code == 200


def test_duplicate_email_rejected(client):
    register_and_login(client)
    dup = client.post(
        "/api/auth/register",
        json={"name": "Clone", "email": "asha@example.com", "password": "anotherpass1"},
    )
    assert dup.status_code == 409


def test_weak_password_rejected(client):
    weak = client.post(
        "/api/auth/register",
        json={"name": "Weak", "email": "weak@example.com", "password": "short"},
    )
    assert weak.status_code == 422


def test_wrong_password(client):
    register_and_login(client)
    bad = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "wrongpassword"})
    assert bad.status_code == 401
    assert "Incorrect" in bad.json()["detail"]


def test_me_requires_auth(client):
    assert client.get("/api/users/me").status_code == 401


def test_access_token_cannot_refresh(client):
    auth = register_and_login(client)
    response = client.post("/api/auth/refresh", json={"refresh_token": auth["headers"]["Authorization"].split()[1]})
    assert response.status_code == 401


def test_password_change(client):
    auth = register_and_login(client)
    wrong_current = client.post(
        "/api/users/me/password",
        headers=auth["headers"],
        json={"current_password": "nope", "new_password": "newsecret99"},
    )
    assert wrong_current.status_code == 400

    ok = client.post(
        "/api/users/me/password",
        headers=auth["headers"],
        json={"current_password": "hunter2secret", "new_password": "newsecret99"},
    )
    assert ok.status_code == 200

    relogin = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "newsecret99"})
    assert relogin.status_code == 200


def test_update_profile_currency(client):
    auth = register_and_login(client)
    updated = client.patch("/api/users/me", headers=auth["headers"], json={"currency": "npr", "name": "Asha R."})
    assert updated.status_code == 200
    body = updated.json()
    assert body["currency"] == "NPR"
    assert body["name"] == "Asha R."
