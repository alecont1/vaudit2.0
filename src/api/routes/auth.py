"""Authentication endpoints."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.schemas.auth import (
    LoginRequest, TokenResponse, SessionInfo,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
)
from src.domain.services.auth import (
    verify_password,
    create_access_token,
    hash_token,
    hash_password,
    verify_token,
    generate_reset_token,
)
from src.domain.services.email import send_password_reset_email
from src.storage.database import get_session
from src.storage.models import User, Session, PasswordResetToken

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_DURATION_MINUTES = 30
MAX_CONCURRENT_SESSIONS = 3


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate user and return JWT token.

    - Returns 401 if credentials invalid
    - Returns 403 if account locked
    - Tracks failed attempts, locks after 3 failures
    - Enforces max 3 concurrent sessions (revokes oldest)
    - Records session with device/IP info
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked until {user.locked_until.isoformat()}",
        )

    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Reset failed attempts on success
    user.failed_login_attempts = 0
    user.locked_until = None

    # Create JWT token
    token, expires_at = create_access_token(
        user_id=user.id,
        email=user.email,
        is_admin=user.is_superuser,
        remember_me=login_data.remember_me,
    )

    # Enforce max concurrent sessions - revoke oldest if at limit
    active_sessions_result = await db.execute(
        select(Session)
        .where(Session.user_id == user.id)
        .where(Session.is_revoked == False)
        .where(Session.expires_at > datetime.utcnow())
        .order_by(Session.created_at.asc())
    )
    active_sessions = list(active_sessions_result.scalars().all())

    if len(active_sessions) >= MAX_CONCURRENT_SESSIONS:
        # Revoke oldest session(s) to make room
        sessions_to_revoke = active_sessions[:len(active_sessions) - MAX_CONCURRENT_SESSIONS + 1]
        for old_session in sessions_to_revoke:
            old_session.is_revoked = True

    # Create session record
    session = Session(
        user_id=user.id,
        token_hash=hash_token(token),
        device_info=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()

    # Calculate expires_in seconds
    expires_in = int((expires_at - datetime.utcnow()).total_seconds())

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Revoke current session.

    Expects Authorization header with Bearer token.
    Returns 204 on success, 401 if token invalid/missing.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = auth_header.split(" ")[1]
    token_hash_value = hash_token(token)

    # Find and revoke session
    result = await db.execute(
        select(Session).where(Session.token_hash == token_hash_value)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    session.is_revoked = True
    await db.commit()

    return None  # 204 No Content


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """List all active sessions for current user.

    Requires valid JWT in Authorization header.
    """
    from src.domain.services.auth import verify_token

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = UUID(payload["sub"])
    current_token_hash = hash_token(token)

    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .where(Session.is_revoked == False)
        .where(Session.expires_at > datetime.utcnow())
        .order_by(Session.created_at.desc())
    )
    sessions = result.scalars().all()

    return [
        SessionInfo(
            id=s.id,
            device_info=s.device_info,
            ip_address=s.ip_address,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_current=(s.token_hash == current_token_hash),
        )
        for s in sessions
    ]
