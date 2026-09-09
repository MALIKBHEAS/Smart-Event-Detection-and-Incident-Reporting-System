from __future__ import annotations

import pytest
from app.db.session import SessionLocal
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture(autouse=True)
def _clean_users():
    def wipe():
        session = SessionLocal()
        session.execute(text("DELETE FROM user_roles"))
        session.execute(text("DELETE FROM refresh_tokens"))
        session.execute(text("DELETE FROM users"))
        session.commit()
        session.close()

    wipe()
    yield
    wipe()


@pytest.fixture()
def admin_headers():
    with TestClient(app) as client:
        client.post("/auth/register", json={"username": "admin", "email": "admin@example.com", "password": "supersecret123"})
        login = client.post("/auth/login", json={"username": "admin", "password": "supersecret123"})
        yield {"Authorization": f"Bearer {login.json()['access_token']}"}, client


def test_admin_can_list_users(admin_headers) -> None:
    headers, client = admin_headers
    resp = client.get("/users", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["username"] == "admin"
    assert "hashed_password" not in body[0]
    assert "password" not in body[0]


def test_admin_can_view_and_manage_other_users(admin_headers) -> None:
    headers, client = admin_headers
    client.post(
        "/auth/register",
        json={"username": "viewer1", "email": "viewer1@example.com", "password": "supersecret123", "role": "Viewer"},
        headers=headers,
    )

    users = client.get("/users", headers=headers).json()
    viewer = next(u for u in users if u["username"] == "viewer1")

    detail = client.get(f"/users/{viewer['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["roles"] == ["Viewer"]

    disable_resp = client.put(f"/users/{viewer['id']}/active", json={"is_active": False}, headers=headers)
    assert disable_resp.status_code == 200
    assert disable_resp.json()["is_active"] is False

    role_resp = client.put(f"/users/{viewer['id']}/roles", json={"roles": ["Security Operator"]}, headers=headers)
    assert role_resp.status_code == 200
    assert role_resp.json()["roles"] == ["Security Operator"]


def test_admin_cannot_deactivate_self(admin_headers) -> None:
    headers, client = admin_headers
    me = client.get("/auth/me", headers=headers).json()
    resp = client.put(f"/users/{me['id']}/active", json={"is_active": False}, headers=headers)
    assert resp.status_code == 400


def test_invalid_role_rejected(admin_headers) -> None:
    headers, client = admin_headers
    me = client.get("/auth/me", headers=headers).json()
    resp = client.put(f"/users/{me['id']}/roles", json={"roles": ["SuperAdmin"]}, headers=headers)
    assert resp.status_code == 400


def test_get_missing_user_404(admin_headers) -> None:
    headers, client = admin_headers
    assert client.get("/users/999999", headers=headers).status_code == 404


def test_non_admin_cannot_access_users(admin_headers) -> None:
    headers, client = admin_headers
    client.post(
        "/auth/register",
        json={"username": "viewer2", "email": "viewer2@example.com", "password": "supersecret123", "role": "Viewer"},
        headers=headers,
    )
    viewer_login = client.post("/auth/login", json={"username": "viewer2", "password": "supersecret123"})
    viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

    assert client.get("/users", headers=viewer_headers).status_code == 403


def test_users_require_authentication() -> None:
    with TestClient(app) as client:
        assert client.get("/users").status_code == 401
