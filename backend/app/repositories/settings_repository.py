from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.settings import AppSettingsRow


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> AppSettingsRow:
        row = self._session.get(AppSettingsRow, 1)
        if row is None:
            # Fallback if the migration seed row is somehow missing (e.g. a
            # DB created via Base.metadata.create_all in tests rather than
            # alembic) -- keeps this repository usable either way.
            row = AppSettingsRow(id=1)
            self._session.add(row)
            self._session.commit()
            self._session.refresh(row)
        return row

    def update(self, **fields) -> AppSettingsRow:
        row = self.get()
        for key, value in fields.items():
            if value is not None:
                setattr(row, key, value)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row
