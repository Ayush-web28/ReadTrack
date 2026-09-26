"""Tests for registration, login and token protection."""

from datetime import datetime, timedelta, timezone

import jwt

from app.security import ALGORITHM, SECRET_KEY, hash_password, verify_password

USER = {"email": "a@example.com", "name": "A", "password": "secret123"}


def test_register_returns_user_without_password(client):
    resp = client.post("/auth/register", json=USER)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_email_is_409_case_insensitive(client):
    client.post("/auth/register", json=USER)
    resp = client.post("/auth/register", json={**USER, "email": "A@EXAMPLE.com"})
    assert resp.status_code == 409


def test_register_validates_input(client):
    assert client.post("/auth/register", json={**USER, "password": "short"}).status_code == 422
    assert client.post("/auth/register", json={**USER, "email": "not-an-email"}).status_code == 422


def test_login_success_returns_bearer_token(client):
    client.post("/auth/register", json=USER)
    resp = client.post("/auth/login", data={"username": USER["email"], "password": USER["password"]})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["access_token"]


def test_login_wrong_password_and_unknown_user_look_identical(client):
    client.post("/auth/register", json=USER)
    wrong = client.post("/auth/login", data={"username": USER["email"], "password": "nope"})
    unknown = client.post("/auth/login", data={"username": "zz@example.com", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()   # no hint about which emails exist


def test_me_requires_token(client, auth):
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers=auth).json()["email"] == "ayush@example.com"


def test_garbage_expired_and_forged_tokens_are_rejected(client, auth):
    def token(key, expires_in):
        exp = datetime.now(timezone.utc) + expires_in
        return jwt.encode({"sub": "1", "exp": exp}, key, algorithm=ALGORITHM)

    long_key = "x" * 40   # a wrong key, long enough to avoid a library warning
    for bad in ("abc", token(SECRET_KEY, timedelta(seconds=-5)), token(long_key, timedelta(hours=1))):
        resp = client.get("/users/me", headers={"Authorization": f"Bearer {bad}"})
        assert resp.status_code == 401


def test_password_hashing_is_salted_and_verifiable():
    h1, h2 = hash_password("secret123"), hash_password("secret123")
    assert h1 != h2                          # random salt -> different hashes
    assert verify_password("secret123", h1)
    assert not verify_password("wrong", h1)
