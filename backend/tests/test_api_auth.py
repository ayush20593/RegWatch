def test_login_success(client, org_and_user):
    resp = client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password(client, org_and_user):
    resp = client.post("/auth/login", json={"email": "test@nbfc.com", "password": "wrong"})
    assert resp.status_code == 401


def test_me_requires_auth(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_after_login(client, org_and_user):
    client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@nbfc.com"
