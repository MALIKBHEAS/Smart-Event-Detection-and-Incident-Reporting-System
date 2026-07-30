from fastapi import APIRouter, Depends, HTTPException, status, Body
from ..schemas.auth import RegisterRequest, TokenResponse, LoginRequest, RoleAssignRequest
from ..core.deps import get_db, get_current_user, require_role
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.auth_service import auth_service
from ..core.audit import log_action
from ..core.security import decode_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register_user(db, payload.email, payload.password, payload.full_name, payload.phone)
    await log_action(db, user.user_id, "register", "users", user.user_id, {"email": user.email})
    return {"user_id": user.user_id, "email": user.email}

@router.post('/login', response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access, refresh = await auth_service.create_tokens(db, user)
    await log_action(db, user.user_id, "login", "users", user.user_id, {})
    return {"access_token": access, "refresh_token": refresh}

@router.post('/refresh', response_model=TokenResponse)
async def refresh(refresh_token: str = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if payload.get('type') != 'refresh':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a refresh token")
    jti = payload.get('jti')
    sub = payload.get('sub')
    res = await auth_service.rotate_refresh_token(db, jti, sub)
    if not res:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or invalid")
    new_refresh, new_jti = res
    access = create_access_token(sub)
    await log_action(db, int(sub), "refresh", "tokens", None, {"old_jti": jti, "new_jti": new_jti})
    return {"access_token": access, "refresh_token": new_refresh}

@router.post('/logout')
async def logout(refresh_token: str = Body(...), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    jti = payload.get('jti')
    await auth_service.revoke_refresh(db, jti)
    await log_action(db, user.user_id, "logout", "tokens", None, {"jti": jti})
    return {"status": "ok"}

@router.post('/roles/assign')
async def assign_role(payload: RoleAssignRequest, db: AsyncSession = Depends(get_db), _=Depends(require_role('admin'))):
    ur = await auth_service.assign_role(db, payload.user_id, payload.role_id)
    await log_action(db, None, "assign_role", "user_roles", None, {"user_id": payload.user_id, "role_id": payload.role_id})
    return {"status": "assigned"}

@router.post('/roles/revoke')
async def revoke_role(payload: RoleAssignRequest, db: AsyncSession = Depends(get_db), _=Depends(require_role('admin'))):
    ok = await auth_service.revoke_role(db, payload.user_id, payload.role_id)
    await log_action(db, None, "revoke_role", "user_roles", None, {"user_id": payload.user_id, "role_id": payload.role_id})
    return {"status": "revoked"}

@router.get('/users')
async def list_users(db: AsyncSession = Depends(get_db), _=Depends(require_role('admin'))):
    users = await auth_service.list_users(db)
    return [{"user_id": u.user_id, "email": u.email, "full_name": u.full_name} for u in users]

@router.get('/users/{user_id}')
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_role('admin'))):
    u = await auth_service.get_user(db, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": u.user_id, "email": u.email, "full_name": u.full_name}

@router.patch('/users/{user_id}/deactivate')
async def deactivate_user(user_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_role('admin'))):
    stmt = await db.execute(select(User).where(User.user_id==user_id))
    user = stmt.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    await log_action(db, None, "deactivate_user", "users", user.user_id, {})
    return {"status": "deactivated"}
