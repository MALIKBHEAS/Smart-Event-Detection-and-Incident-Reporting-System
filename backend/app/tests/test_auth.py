"""Tests for the authentication & authorization system."""
from __future__ import annotations

import pytest
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.schemas import RegisterRequest
from app.auth.security import hash_password, verify_password
from app.auth.service import AuthError, AuthService
from app.db.base import Base
from app.settings import AppSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Pure unit tests
# ---------------------------------------------------------------------------


def test_password_hash_and_verify_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong password", hashed) is False


def test_verify_password_rejects_malformed_hash_without_raising() -> None:
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


# ---------------------------------------------------------------------------
# Service-level integration tests against an isolated in-memory DB
# ---------------------------------------------------------------------------


@pytest.fixture()
def auth_service():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    session = SessionFactory()

    settings = AppSettings(jwt_secret_key="test-secret", app_env="test")
    service = AuthService(UserRepository(session), RefreshTokenRepository(session), settings)
    yield service
    session.close()


def test_bootstrap_registration_becomes_admin(auth_service: AuthService) -> None:
    user = auth_service.register(
        RegisterRequest(username="first", email="first@example.com", password="supersecret123", role="Viewer"),
        acting_user=None,
    )
    # role="Viewer" was requested but bootstrap always wins -> Admin
    assert [r.name for r in user.roles] == ["Admin"]


def test_second_registration_requires_admin(auth_service: AuthService) -> None:
    admin = auth_service.register(
        RegisterRequest(username="admin", email="admin@example.com", password="supersecret123"),
        acting_user=None,
    )

    with pytest.raises(AuthError) as exc_info:
        auth_service.register(
            RegisterRequest(username="second", email="second@example.com", password="supersecret123"),
            acting_user=None,
        )
    assert exc_info.value.status_code == 401

    # A non-admin can't create users either
    viewer = auth_service.register(
        RegisterRequest(username="viewer", email="viewer@example.com", password="supersecret123", role="Viewer"),
        acting_user=admin,
    )
    with pytest.raises(AuthError) as exc_info:
        auth_service.register(
            RegisterRequest(username="third", email="third@example.com", password="supersecret123"),
            acting_user=viewer,
        )
    assert exc_info.value.status_code == 403

    # An admin can
    created = auth_service.register(
        RegisterRequest(username="fourth", email="fourth@example.com", password="supersecret123", role="Security Operator"),
        acting_user=admin,
    )
    assert [r.name for r in created.roles] == ["Security Operator"]


def test_duplicate_username_and_email_rejected(auth_service: AuthService) -> None:
    auth_service.register(
        RegisterRequest(username="dupe", email="dupe@example.com", password="supersecret123"),
        acting_user=None,
    )
    admin = auth_service.user_repo.get_by_username("dupe")

    with pytest.raises(AuthError) as exc_info:
        auth_service.register(
            RegisterRequest(username="dupe", email="other@example.com", password="supersecret123"),
            acting_user=admin,
        )
    assert exc_info.value.status_code == 409

    with pytest.raises(AuthError) as exc_info:
        auth_service.register(
            RegisterRequest(username="other", email="dupe@example.com", password="supersecret123"),
            acting_user=admin,
        )
    assert exc_info.value.status_code == 409


def test_authenticate_rejects_wrong_password(auth_service: AuthService) -> None:
    auth_service.register(
        RegisterRequest(username="bob", email="bob@example.com", password="correct-password-123"),
        acting_user=None,
    )
    with pytest.raises(AuthError):
        auth_service.authenticate("bob", "wrong-password")

    user = auth_service.authenticate("bob", "correct-password-123")
    assert user.username == "bob"


def test_issue_and_validate_access_token(auth_service: AuthService) -> None:
    user = auth_service.register(
        RegisterRequest(username="carol", email="carol@example.com", password="supersecret123"),
        acting_user=None,
    )
    access_token, _refresh_token = auth_service.issue_tokens(user)
    resolved = auth_service.get_user_from_access_token(access_token)
    assert resolved.username == "carol"


def test_refresh_rotates_token_and_invalidates_old_one(auth_service: AuthService) -> None:
    user = auth_service.register(
        RegisterRequest(username="dan", email="dan@example.com", password="supersecret123"),
        acting_user=None,
    )
    _access, refresh_token = auth_service.issue_tokens(user)

    new_access, new_refresh = auth_service.refresh(refresh_token)
    assert new_access
    assert new_refresh != refresh_token

    # Old refresh token is now revoked (rotation) -- replay must fail.
    with pytest.raises(AuthError):
        auth_service.refresh(refresh_token)

    # The new one still works.
    auth_service.refresh(new_refresh)


def test_logout_revokes_refresh_token(auth_service: AuthService) -> None:
    user = auth_service.register(
        RegisterRequest(username="erin", email="erin@example.com", password="supersecret123"),
        acting_user=None,
    )
    _access, refresh_token = auth_service.issue_tokens(user)

    auth_service.logout(refresh_token)

    with pytest.raises(AuthError):
        auth_service.refresh(refresh_token)


def test_invalid_access_token_rejected(auth_service: AuthService) -> None:
    with pytest.raises(AuthError):
        auth_service.get_user_from_access_token("not-a-real-token")


# ---------------------------------------------------------------------------
# Router-level tests (full stack) -- protected routes actually enforce auth
# ---------------------------------------------------------------------------


def test_protected_routes_require_auth_end_to_end(monkeypatch) -> None:
    import app.db.session as app_db_session
    from app.main import app
    from app.providers.worker_manager_provider import MockWorkerManager
    from fastapi.testclient import TestClient

    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    original_engine = app_db_session.engine
    original_session_local = app_db_session.SessionLocal
    app_db_session.engine = engine
    app_db_session.SessionLocal = SessionFactory

    monkeypatch.setattr(
        "app.providers.worker_manager_provider.create_worker_manager",
        lambda settings=None: MockWorkerManager(),
    )

    try:
        with TestClient(app) as client:
            # No token at all -> 401 on protected routes.
            assert client.get("/cameras").status_code == 401
            assert client.get("/analytics/overview").status_code == 401
            assert client.post("/workers/start/1").status_code == 401

            # /health stays public (infra health checks shouldn't need auth).
            assert client.get("/health").status_code == 200

            # Bootstrap admin, log in.
            reg = client.post(
                "/auth/register",
                json={"username": "admin", "email": "admin@example.com", "password": "supersecret123"},
            )
            assert reg.status_code == 201
            login = client.post("/auth/login", json={"username": "admin", "password": "supersecret123"})
            assert login.status_code == 200
            token = login.json()["access_token"]

            headers = {"Authorization": f"Bearer {token}"}
            assert client.get("/cameras", headers=headers).status_code == 200
            assert client.get("/analytics/overview", headers=headers).status_code == 200

            # Viewer role cannot write cameras.
            viewer_reg = client.post(
                "/auth/register",
                json={"username": "viewer", "email": "viewer@example.com", "password": "supersecret123", "role": "Viewer"},
                headers=headers,
            )
            assert viewer_reg.status_code == 201
            viewer_login = client.post("/auth/login", json={"username": "viewer", "password": "supersecret123"})
            viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

            create_resp = client.post(
                "/cameras",
                json={"name": "Cam", "rtsp_url": "rtsp://x", "location": None, "enabled": True},
                headers=viewer_headers,
            )
            assert create_resp.status_code == 403

            # Admin can.
            create_resp = client.post(
                "/cameras",
                json={"name": "Cam", "rtsp_url": "rtsp://x", "location": None, "enabled": True},
                headers=headers,
            )
            assert create_resp.status_code == 201
    finally:
        app_db_session.engine.dispose()
        app_db_session.engine = original_engine
        app_db_session.SessionLocal = original_session_local
