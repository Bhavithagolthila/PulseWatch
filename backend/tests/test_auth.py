import time

import pytest

from app.services import auth


def login(client, username="owner", password="test-password"):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_login_success_returns_token_that_works(anon_client):
    response = login(anon_client)
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json() == {"username": "owner"}


@pytest.mark.parametrize("username,password", [("owner", "wrong"), ("someone", "test-password"), ("", "")])
def test_login_rejects_bad_credentials(anon_client, username, password):
    assert login(anon_client, username, password).status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/monitors"),
        ("post", "/api/monitors"),
        ("get", "/api/dashboard/stats"),
        ("get", "/api/dashboard/response-times"),
        ("get", "/api/incidents"),
        ("get", "/api/alerts/config"),
        ("post", "/api/alerts/test"),
        ("post", "/api/monitors/1/check"),
    ],
)
def test_protected_routes_need_login(anon_client, method, path):
    assert getattr(anon_client, method)(path).status_code == 401


def test_health_stays_public(anon_client):
    assert anon_client.get("/api/health").status_code == 200


def test_garbage_and_tampered_tokens_are_rejected(anon_client):
    token = login(anon_client).json()["access_token"]
    payload, signature = token.split(".")
    for bad in ["nonsense", "a.b", f"{payload}.{signature[:-2]}xx", f"{payload}x.{signature}"]:
        assert anon_client.get("/api/monitors", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_expired_token_is_rejected():
    token, _ = auth.create_token("owner", now=time.time() - 13 * 3600)  # TTL is 12 h
    assert auth.verify_token(token) is None


def test_token_signed_with_another_key_is_rejected(monkeypatch):
    token, _ = auth.create_token("owner")
    monkeypatch.setattr(auth.settings, "secret_key", "different-key")
    assert auth.verify_token(token) is None


def test_login_refused_when_not_configured(anon_client, monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_password", "")
    response = login(anon_client)
    assert response.status_code == 503
    assert "AUTH_PASSWORD" in response.json()["detail"]
