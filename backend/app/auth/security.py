"""Password hashing and JWT encode/decode helpers.

Uses bcrypt directly (not passlib) to avoid passlib's bcrypt backend
version-detection issues with bcrypt>=4.1, and PyJWT for tokens (no extra
crypto backend to configure for HS256).
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, cast

import bcrypt
import jwt

from app.settings import AppSettings


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash (e.g. legacy/corrupt data) -- treat as no match
        # rather than raising, so a bad stored hash can't 500 the login route.
        return False


def create_access_token(*, subject: str, roles: list[str], settings: AppSettings) -> str:
    return _encode_token(
        subject=subject,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
        settings=settings,
        extra_claims={"roles": roles},
    )


def create_refresh_token(*, subject: str, settings: AppSettings) -> tuple[str, str, datetime]:
    """Returns (token, token_hash, expires_at). The caller persists
    token_hash (never the raw token) so a leaked DB dump can't be replayed
    as a valid refresh token."""
    jti = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    token = _encode_token(
        subject=subject,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
        settings=settings,
        extra_claims={"jti": jti},
    )
    token_hash = hash_token(token)
    return token, token_hash, expires_at


def hash_token(token: str) -> str:
    """One-way hash used to look up/compare refresh tokens without storing
    the raw token value in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _encode_token(
    *,
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    settings: AppSettings,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, *, settings: AppSettings, expected_type: Optional[TokenType] = None) -> Dict[str, Any]:
    """Raises jwt.PyJWTError (or a subclass) on any invalid/expired/wrong-type token."""
    payload = cast(Dict[str, Any], jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]))
    if expected_type is not None and payload.get("type") != expected_type.value:
        raise jwt.InvalidTokenError(f"Expected a {expected_type.value} token")
    return payload
