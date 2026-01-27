"""Authentication endpoints."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func, update
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
RESET_TOKEN_EXPIRE_MINUTES = 15


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
        session_ids_to_revoke = [s.id for s in sessions_to_revoke]
        await db.execute(
            update(Session)
            .where(Session.id.in_(session_ids_to_revoke))
            .values(is_revoked=True)
        )
        await db.flush()  # Ensure revocation is written before creating new session

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
        select(Session)
        .where(Session.token_hash == token_hash_value)
        .order_by(Session.created_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()

    if not session or session.is_revoked:
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


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: Request,
    password_data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_session),
):
    """Change password for authenticated user.

    Requires valid JWT in Authorization header.
    Validates current password before accepting new password.
    Clears must_change_password flag on success.
    """
    # Get current user from token
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

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Verify current password
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    user.hashed_password = hash_password(password_data.new_password)
    user.must_change_password = False
    user.updated_at = datetime.utcnow()

    await db.commit()

    return None  # 204 No Content


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_session),
):
    """Request password reset email.

    Always returns 202 to prevent email enumeration.
    Only sends email if user exists.
    """
    result = await db.execute(
        select(User).where(User.email == reset_request.email)
    )
    user = result.scalar_one_or_none()

    if user:
        # Generate reset token
        reset_token = generate_reset_token()

        # Create token record
        token_record = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(reset_token),
            expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        )
        db.add(token_record)
        await db.commit()

        # Send email (async, but we don't await in production for faster response)
        await send_password_reset_email(user.email, reset_token)

    # Always return success to prevent email enumeration
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_session),
):
    """Reset password using reset token from email.

    Validates token is valid, not expired, and not used.
    Sets new password and marks token as used.
    """
    token_hash_value = hash_token(reset_data.token)

    # Find token
    result = await db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash_value)
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Check if expired
    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    # Check if already used
    if token_record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used",
        )

    # Get user
    user_result = await db.execute(
        select(User).where(User.id == token_record.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Update password
    user.hashed_password = hash_password(reset_data.new_password)
    user.must_change_password = False
    user.failed_login_attempts = 0  # Clear any lockout
    user.locked_until = None
    user.updated_at = datetime.utcnow()

    # Mark token as used
    token_record.used_at = datetime.utcnow()

    await db.commit()

    return None  # 204 No Content
