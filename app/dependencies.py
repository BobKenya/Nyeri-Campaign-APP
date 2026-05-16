"""Shared dependencies: current user, role guards."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.utils.security import decode_token

security_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    from app.models.auth import User
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.user_id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user

def require_roles(*allowed_roles: str):
    async def _guard(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        from app.models.auth import Role
        result = await db.execute(select(Role).where(Role.role_id == current_user.role_id))
        role = result.scalar_one_or_none()
        if not role or role.role_name not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return _guard

require_admin = require_roles("admin", "super_admin")
require_coordinator = require_roles("admin", "super_admin", "coordinator")
require_field_agent = require_roles("admin", "super_admin", "coordinator", "field_agent")
