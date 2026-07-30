from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.session import AsyncSessionLocal
from ..core.security import decode_token

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(token: str = Depends(lambda: None)):
    # Minimal stub: in real app use OAuth2PasswordBearer; here return a fake user for initial scaffold
    class User:
        user_id = 1
    return User()
