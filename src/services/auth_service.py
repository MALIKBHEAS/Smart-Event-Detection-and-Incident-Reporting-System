from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update
from datetime import datetime, timedelta
from ..models.all_models import User, UserRole, Role, RefreshToken
from ..core.security import hash_password, verify_password, create_access_token, create_refresh_token
import typing

class AuthService:
    async def register_user(self, db: AsyncSession, email: str, password: str, full_name: typing.Optional[str] = None, phone: typing.Optional[str] = None):
        pwd = hash_password(password)
        u = User(email=email, password_hash=pwd, full_name=full_name, phone=phone)
        db.add(u)
        await db.commit()
        await db.refresh(u)
        return u

    async def authenticate_user(self, db: AsyncSession, email: str, password: str):
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        user = res.scalars().first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def create_tokens(self, db: AsyncSession, user: User):
        access = create_access_token(str(user.user_id))
        refresh_token, jti = create_refresh_token(str(user.user_id))
        # store refresh token record
        expires_at = datetime.utcnow() + timedelta(days=30)
        rt = RefreshToken(token_id=jti, user_id=user.user_id, revoked=False, created_at=datetime.utcnow(), expires_at=expires_at)
        db.add(rt)
        await db.commit()
        return access, refresh_token

    async def rotate_refresh_token(self, db: AsyncSession, old_jti: str, subject: str):
        # revoke old and create new
        stmt = select(RefreshToken).where(RefreshToken.token_id == old_jti)
        res = await db.execute(stmt)
        token = res.scalars().first()
        if not token or token.revoked:
            return None
        # revoke
        token.revoked = True
        new_refresh, new_jti = create_refresh_token(subject)
        expires_at = datetime.utcnow() + timedelta(days=30)
        new_token = RefreshToken(token_id=new_jti, user_id=int(subject), revoked=False, created_at=datetime.utcnow(), expires_at=expires_at, replaced_by=None)
        token.replaced_by = new_jti
        db.add(new_token)
        await db.commit()
        return new_refresh, new_jti

    async def revoke_refresh(self, db: AsyncSession, jti: str):
        stmt = select(RefreshToken).where(RefreshToken.token_id == jti)
        res = await db.execute(stmt)
        token = res.scalars().first()
        if token:
            token.revoked = True
            await db.commit()
            return True
        return False

    async def assign_role(self, db: AsyncSession, user_id: int, role_id: int):
        ur = UserRole(user_id=user_id, role_id=role_id)
        db.add(ur)
        await db.commit()
        return ur

    async def revoke_role(self, db: AsyncSession, user_id: int, role_id: int):
        stmt = select(UserRole).where(UserRole.user_id==user_id, UserRole.role_id==role_id)
        res = await db.execute(stmt)
        ur = res.scalars().first()
        if ur:
            await db.delete(ur)
            await db.commit()
            return True
        return False

    async def list_users(self, db: AsyncSession):
        stmt = select(User)
        res = await db.execute(stmt)
        return res.scalars().all()

    async def get_user(self, db: AsyncSession, user_id: int):
        stmt = select(User).where(User.user_id == user_id)
        res = await db.execute(stmt)
        return res.scalars().first()


auth_service = AuthService()
