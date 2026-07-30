from sqlalchemy.ext.asyncio import AsyncSession
from ..models.all_models import AuditLog
from datetime import datetime

async def log_action(db: AsyncSession, user_id: int, action: str, target_table: str, target_id: int, details: dict):
    a = AuditLog(user_id=user_id, action=action, target_table=target_table, target_id=target_id, details=details, created_at=datetime.utcnow())
    db.add(a)
    await db.commit()
