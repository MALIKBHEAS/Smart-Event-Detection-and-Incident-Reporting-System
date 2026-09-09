from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.service import AuthError, AuthService
from app.db.session import get_db
from app.models.user import User
from app.settings import AppSettings, get_settings

_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(
    db: Session = Depends(get_db),
    settings: AppSettings = Depends(get_settings),
) -> AuthService:
    return AuthService(UserRepository(db), RefreshTokenRepository(db), settings)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return auth_service.get_user_from_access_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User | None:
    if credentials is None:
        return None
    try:
        return auth_service.get_user_from_access_token(credentials.credentials)
    except AuthError:
        return None


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """Dependency factory: require the current user to hold at least one of
    the given roles. Usage: Depends(require_role("Admin"))."""

    def _check(user: User = Depends(get_current_user)) -> User:
        user_roles = {role.name for role in user.roles}
        if not user_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return _check
