from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.dependencies.worker_manager import get_worker_manager
from app.models.camera import Camera
from app.models.user import User
from app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate
from app.services.camera_service import CameraNotFoundError, CameraService
from app.workers.protocols import WorkerManagerProtocol

router = APIRouter(prefix="/cameras", tags=["cameras"])

_can_write = require_role("Admin", "Security Operator")


def get_camera_service(
    db: Session = Depends(get_db),
    worker_manager: WorkerManagerProtocol = Depends(get_worker_manager),
) -> CameraService:
    return CameraService(db, worker_manager)


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_in: CameraCreate,
    service: CameraService = Depends(get_camera_service),
    _user: User = Depends(_can_write),
) -> CameraResponse:
    camera = await service.create_camera(camera_in)
    return camera


@router.get("", response_model=List[CameraResponse])
def list_cameras(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> List[Camera]:
    service = CameraService(db)
    return service.list_cameras()


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> CameraResponse:
    service = CameraService(db)
    try:
        return service.get_camera(camera_id)
    except CameraNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    camera_in: CameraUpdate,
    service: CameraService = Depends(get_camera_service),
    _user: User = Depends(_can_write),
) -> CameraResponse:
    try:
        return await service.update_camera(camera_id, camera_in)
    except CameraNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: int,
    service: CameraService = Depends(get_camera_service),
    _user: User = Depends(_can_write),
) -> None:
    try:
        await service.delete_camera(camera_id)
    except CameraNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
