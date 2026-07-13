def test_register_returns_token_and_user(client):
    response = client.post("/auth/register", json={"username": "alice", "password": "password123"})

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "alice"


def test_login_returns_token_for_valid_credentials(client):
    client.post("/auth/register", json={"username": "alice", "password": "password123"})

    response = client.post("/auth/login", json={"username": "alice", "password": "password123"})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_protected_route_rejects_missing_token(client):
    response = client.get("/rooms")

    assert response.status_code == 401


def test_protected_route_rejects_invalid_token(client):
    response = client.get("/rooms", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
