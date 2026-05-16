"""Auth routes: login, register, refresh, 2FA, user management."""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_db
from app.models.auth import User, Role, UserSession, Notification
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    UserCreate, UserUpdate, UserResponse, RoleResponse, NotificationResponse,
)
from app.utils.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, verify_totp, generate_totp_secret, get_totp_uri,
)
from app.dependencies import get_current_user, require_admin
from app.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.account_locked_until and user.account_locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account temporarily locked")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    # 2FA check
    if user.two_factor_enabled:
        if not body.totp_code:
            raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail="2FA code required")
        if not verify_totp(user.two_factor_secret, body.totp_code):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")

    # Reset failed login count
    user.failed_login_count = 0
    user.last_login = datetime.now(timezone.utc)

    # Create session
    session = UserSession(
        user_id=user.user_id,
        ip_address=request.client.host if request.client else None,
        device_info=request.headers.get("user-agent", ""),
    )
    db.add(session)

    token_data = {"sub": str(user.user_id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.user_id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_data = {"sub": str(user.user_id), "email": user.email}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role_id=body.role_id,
        phone_number=body.phone_number,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change current user's password"""
    old_password = body.get("old_password")
    new_password = body.get("new_password")
    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="old_password and new_password required")
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    current_user.password_hash = hash_password(new_password)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.post("/2fa/enable")
async def enable_2fa(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    secret = generate_totp_secret()
    current_user.two_factor_secret = secret
    uri = get_totp_uri(secret, current_user.email)
    return {"secret": secret, "provisioning_uri": uri}


@router.post("/2fa/confirm")
async def confirm_2fa(code: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.two_factor_secret:
        raise HTTPException(status_code=400, detail="Call /2fa/enable first")
    if not verify_totp(current_user.two_factor_secret, code):
        raise HTTPException(status_code=400, detail="Invalid code")
    current_user.two_factor_enabled = True
    return {"message": "2FA enabled"}


@router.get("/notifications", response_model=list[NotificationResponse])
async def get_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.notification_id == notification_id, Notification.user_id == current_user.user_id)
        .values(read_at=datetime.now(timezone.utc))
    )
    return {"message": "Marked as read"}
