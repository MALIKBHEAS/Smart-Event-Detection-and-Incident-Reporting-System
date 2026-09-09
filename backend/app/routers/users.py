from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.auth.repository import UserRepository
from app.auth.schemas import VALID_ROLES, UserResponse
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])

# Every route in this router is Admin-only: it exposes other users' emails,
# roles, and active status, and lets an Admin disable accounts or change
# roles -- not something a Security Operator or Viewer should be able to do
# or even see the full list for.
_admin_only = require_role("Admin")


class UserActiveUpdate(BaseModel):
    is_active: bool


class UserRolesUpdate(BaseModel):
    roles: List[str]


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=int(user.id),
        username=str(user.username),
        email=str(user.email),
        is_active=bool(user.is_active),
        roles=[role.name for role in user.roles],
    )


@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), _user: User = Depends(_admin_only)) -> List[UserResponse]:
    return [_to_response(u) for u in UserRepository(db).list()]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), _user: User = Depends(_admin_only)) -> UserResponse:
    user = UserRepository(db).get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_response(user)


@router.put("/{user_id}/active", response_model=UserResponse)
def set_user_active(
    user_id: int,
    payload: UserActiveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_only),
) -> UserResponse:
    repo = UserRepository(db)
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if int(user.id) == int(current_user.id) and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't deactivate your own account.")
    return _to_response(repo.set_active(user, payload.is_active))


@router.put("/{user_id}/roles", response_model=UserResponse)
def set_user_roles(
    user_id: int,
    payload: UserRolesUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_admin_only),
) -> UserResponse:
    invalid = set(payload.roles) - VALID_ROLES
    if invalid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role(s): {', '.join(sorted(invalid))}")
    repo = UserRepository(db)
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_response(repo.set_roles(user, payload.roles))
