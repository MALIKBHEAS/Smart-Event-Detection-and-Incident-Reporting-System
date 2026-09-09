from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_auth_service, get_current_user, get_current_user_optional
from app.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.service import AuthError, AuthService
from app.models.user import User
from app.settings import AppSettings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=int(user.id),
        username=str(user.username),
        email=str(user.email),
        is_active=bool(user.is_active),
        roles=[role.name for role in user.roles],
    )


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User | None = Depends(get_current_user_optional),
) -> UserResponse:
    # Bootstrap-or-admin-only logic lives in AuthService.register: the very
    # first (bootstrap) registration against an empty database succeeds with
    # no token at all; every registration after that requires the caller to
    # be an authenticated Admin (current_user, resolved here if a valid
    # bearer token was sent -- None otherwise, which AuthService.register
    # turns into a 401).
    try:
        user = auth_service.register(payload, acting_user=current_user)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return _user_response(user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    settings: AppSettings = Depends(get_settings),
) -> TokenResponse:
    try:
        user = auth_service.authenticate(payload.username, payload.password)
        access_token, refresh_token = auth_service.issue_tokens(user)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
    settings: AppSettings = Depends(get_settings),
) -> TokenResponse:
    try:
        access_token, new_refresh_token = auth_service.refresh(payload.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)) -> None:
    auth_service.logout(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(current_user)
