from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

VALID_ROLES = {"Admin", "Security Operator", "Viewer"}


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds, for the access token


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    # Ignored unless this is the bootstrap (first-ever) user, who always
    # becomes Admin regardless of what's requested here -- see
    # AuthService.register. Otherwise only an existing Admin can create
    # users (via this same endpoint) and choose their role explicitly.
    role: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
        return value


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    roles: List[str]
