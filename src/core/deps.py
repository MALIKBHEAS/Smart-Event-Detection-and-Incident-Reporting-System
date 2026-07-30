from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.session import AsyncSessionLocal
from ..core.security import decode_token
from ..models.all_models import User, Role, UserRole
from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    stmt = select(User).where(User.user_id == int(sub))
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user

def require_role(role_name: str):
    async def role_dependency(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        stmt = select(Role).where(Role.role_name == role_name)
        res = await db.execute(stmt)
        role = res.scalars().first()
        if not role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not found")
        stmt2 = select(UserRole).where(UserRole.user_id == user.user_id, UserRole.role_id == role.role_id)
        res2 = await db.execute(stmt2)
        ur = res2.scalars().first()
        if not ur:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return True
    return role_dependency
