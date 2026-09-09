from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import TokenType, decode_token
from app.db.session import SessionLocal, get_db
from app.models.user import User
from app.notifications.manager import connection_manager
from app.notifications.repository import NotificationRepository
from app.schemas.notification import NotificationResponse, PaginatedNotificationsResponse
from app.settings import get_settings

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=PaginatedNotificationsResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> PaginatedNotificationsResponse:
    repo = NotificationRepository(db)
    items, total = repo.list(page=page, page_size=page_size, unread_only=unread_only)
    return PaginatedNotificationsResponse(
        items=[NotificationResponse.model_validate(i) for i in items],
        total=total,
        unread_count=repo.unread_count(),
        page=page,
        page_size=page_size,
    )


@router.put("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> NotificationResponse:
    record = NotificationRepository(db).mark_read(notification_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationResponse.model_validate(record)


@router.put("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    count = NotificationRepository(db).mark_all_read()
    return {"marked_read": count}


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket, token: str = Query(...)) -> None:
    """Browser WebSocket clients can't set an Authorization header, so the
    access token is passed as a query param -- same JWT, same validation as
    every other authenticated endpoint."""
    settings = get_settings()
    try:
        payload = decode_token(token, settings=settings, expected_type=TokenType.ACCESS)
        user_id = int(payload["sub"])
    except jwt.PyJWTError:
        await websocket.close(code=4401)
        return

    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            await websocket.close(code=4401)
            return
    finally:
        session.close()

    await connection_manager.connect(websocket)
    try:
        while True:
            # Clients don't need to send anything; this just detects disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)
