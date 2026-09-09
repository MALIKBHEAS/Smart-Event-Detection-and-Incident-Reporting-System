from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        type: str,
        message: str,
        severity: str = "low",
        related_type: Optional[str] = None,
        related_id: Optional[int] = None,
    ) -> Notification:
        record = Notification(
            type=type,
            message=message,
            severity=severity,
            related_type=related_type,
            related_id=related_id,
            read=False,
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def list(self, *, page: int = 1, page_size: int = 20, unread_only: bool = False) -> Tuple[List[Notification], int]:
        query = self._session.query(Notification)
        if unread_only:
            query = query.filter(Notification.read.is_(False))
        total = query.count()
        query = query.order_by(Notification.created_at.desc())
        rows = query.offset((max(page, 1) - 1) * page_size).limit(page_size).all()
        return rows, total

    def unread_count(self) -> int:
        return self._session.query(Notification).filter(Notification.read.is_(False)).count()

    def mark_read(self, notification_id: int) -> Optional[Notification]:
        record = self._session.get(Notification, notification_id)
        if record is None:
            return None
        record.read = True  # type: ignore[assignment]
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def mark_all_read(self) -> int:
        count = self._session.query(Notification).filter(Notification.read.is_(False)).update({"read": True})
        self._session.commit()
        return count
