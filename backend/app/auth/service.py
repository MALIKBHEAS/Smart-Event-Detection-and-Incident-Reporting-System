"""Auth business logic: login, token refresh, logout, and the bootstrap /
admin-gated user registration flow."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import jwt

from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.schemas import RegisterRequest
from app.auth.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.settings import AppSettings


class AuthError(Exception):
    """Raised for any auth failure the router should turn into a 401/403/409."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthService:
    def __init__(self, user_repo: UserRepository, refresh_repo: RefreshTokenRepository, settings: AppSettings) -> None:
        self.user_repo = user_repo
        self.refresh_repo = refresh_repo
        self.settings = settings

    # -- registration ------------------------------------------------------

    def register(self, payload: RegisterRequest, *, acting_user: Optional[User]) -> User:
        """Create a user.

        Bootstrap rule: if there are zero users in the system, the very
        first registration is allowed without authentication and always
        becomes Admin (otherwise nobody could ever log in to a fresh
        install). After that, only an authenticated Admin may register new
        users, and the role they request is honored.
        """
        is_bootstrap = self.user_repo.count() == 0

        if not is_bootstrap:
            if acting_user is None:
                raise AuthError("Registration requires authentication.", status_code=401)
            if "Admin" not in self.role_names(acting_user):
                raise AuthError("Only Admins can register new users.", status_code=403)

        if self.user_repo.get_by_username(payload.username) is not None:
            raise AuthError("Username already taken.", status_code=409)
        if self.user_repo.get_by_email(payload.email) is not None:
            raise AuthError("Email already registered.", status_code=409)

        role_name = "Admin" if is_bootstrap else (payload.role or "Viewer")
        role = self.user_repo.get_or_create_role(role_name)

        user = User(
            username=payload.username,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            is_active=True,
        )
        user.roles = [role]
        self.user_repo.add(user)
        self.user_repo.commit()
        return user

    # -- login / tokens ------------------------------------------------------

    def authenticate(self, username: str, password: str) -> User:
        user = self.user_repo.get_by_username(username)
        if user is None or not verify_password(password, str(user.hashed_password)):
            raise AuthError("Invalid username or password.")
        if not user.is_active:
            raise AuthError("This account has been deactivated.", status_code=403)
        return user

    def issue_tokens(self, user: User) -> tuple[str, str]:
        roles = [role.name for role in user.roles]
        user_id = int(user.id)
        access_token = create_access_token(subject=str(user_id), roles=roles, settings=self.settings)
        refresh_token, token_hash, expires_at = create_refresh_token(subject=str(user_id), settings=self.settings)
        self.refresh_repo.add(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.refresh_repo.commit()
        return access_token, refresh_token

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Validates + rotates a refresh token, returning a new (access, refresh) pair."""
        try:
            payload = decode_token(refresh_token, settings=self.settings, expected_type=TokenType.REFRESH)
        except jwt.PyJWTError:
            raise AuthError("Invalid or expired refresh token.")

        token_hash = hash_token(refresh_token)
        record = self.refresh_repo.get_by_hash(token_hash)
        if record is None or record.revoked:
            raise AuthError("Refresh token has been revoked.")
        if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise AuthError("Refresh token has expired.")

        user = self.user_repo.get(int(payload["sub"]))
        if user is None or not user.is_active:
            raise AuthError("Account no longer available.", status_code=403)

        # Rotate: revoke the used refresh token and issue a fresh pair, so a
        # stolen-and-replayed refresh token gets invalidated the moment the
        # legitimate client also tries to use it.
        self.refresh_repo.revoke(record)
        access_token, new_refresh_token = self.issue_tokens(user)
        return access_token, new_refresh_token

    def logout(self, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        record = self.refresh_repo.get_by_hash(token_hash)
        if record is not None and not record.revoked:
            self.refresh_repo.revoke(record)
            self.refresh_repo.commit()

    def get_user_from_access_token(self, token: str) -> User:
        try:
            payload = decode_token(token, settings=self.settings, expected_type=TokenType.ACCESS)
        except jwt.PyJWTError:
            raise AuthError("Invalid or expired access token.")
        user = self.user_repo.get(int(payload["sub"]))
        if user is None or not user.is_active:
            raise AuthError("Account no longer available.", status_code=403)
        return user

    @staticmethod
    def role_names(user: User) -> List[str]:
        return [role.name for role in user.roles]
