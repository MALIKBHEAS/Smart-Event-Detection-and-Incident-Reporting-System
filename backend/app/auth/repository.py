from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.models.user import Role, User


class UserRepository:
    """Repository for user/role persistence (mirrors CameraRepository's
    session-injected style)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int) -> Optional[User]:
        return self._session.get(User, user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        return self._session.query(User).filter(User.username == username).one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        return self._session.query(User).filter(User.email == email).one_or_none()

    def list(self) -> List[User]:
        return self._session.query(User).order_by(User.id).all()

    def set_active(self, user: User, is_active: bool) -> User:
        user.is_active = is_active  # type: ignore[assignment]
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def set_roles(self, user: User, role_names: List[str]) -> User:
        user.roles = [self.get_or_create_role(name) for name in role_names]
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def count(self) -> int:
        return self._session.query(User).count()

    def add(self, user: User) -> User:
        self._session.add(user)
        self._session.flush()
        return user

    def get_or_create_role(self, name: str) -> Role:
        role = self._session.query(Role).filter(Role.name == name).one_or_none()
        if role is None:
            role = Role(name=name)
            self._session.add(role)
            self._session.flush()
        return role

    def commit(self) -> None:
        self._session.commit()


class RefreshTokenRepository:
    """Repository for refresh-token persistence, enabling real revocation
    on logout (unlike a purely stateless JWT refresh token)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, *, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        record = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at, revoked=False)
        self._session.add(record)
        self._session.flush()
        return record

    def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        return self._session.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).one_or_none()

    def revoke(self, record: RefreshToken) -> None:
        record.revoked = True  # type: ignore[assignment]
        self._session.add(record)

    def revoke_all_for_user(self, user_id: int) -> None:
        self._session.query(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.revoked == False).update(  # noqa: E712
            {"revoked": True}
        )

    def commit(self) -> None:
        self._session.commit()
