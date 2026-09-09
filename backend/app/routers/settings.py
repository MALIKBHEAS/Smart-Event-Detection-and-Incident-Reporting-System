from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

_can_write = require_role("Admin")


@router.get("", response_model=SettingsResponse)
def get_settings_endpoint(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> SettingsResponse:
    return SettingsResponse.model_validate(SettingsRepository(db).get())


@router.put("", response_model=SettingsResponse)
def update_settings_endpoint(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_can_write),
) -> SettingsResponse:
    row = SettingsRepository(db).update(**payload.model_dump(exclude_unset=True))
    return SettingsResponse.model_validate(row)
