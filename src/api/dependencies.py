"""Shared FastAPI dependencies.

Central location for dependency injection functions.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.services.auth import verify_token, hash_token
from src.storage.database import get_session
from src.storage.models import User, Session

__all__ = ["get_session", "get_current_user", "require_auth", "require_admin"]


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User | None:
    """Get current user from JWT token if present.

    Returns None if no token or invalid token.
    Use require_auth for endpoints that must have authentication.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        return None

    # Verify session is still valid (not revoked)
    token_hash_value = hash_token(token)
    session_result = await db.execute(
        select(Session)
        .where(Session.token_hash == token_hash_value)
        .where(Session.is_revoked == False)
        .order_by(Session.created_at.desc())
        .limit(1)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        return None

    # Get user
    user_id = UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    return user


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Require valid authentication.

    Returns the authenticated user.
    Raises 401 if not authenticated.
    Raises 403 if user must change password (except for password change endpoint).
    """
    user = await get_current_user(request, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Check must_change_password - allow only password change endpoint
    if user.must_change_password:
        # Allow access to password change endpoint
        if request.url.path == "/auth/change-password":
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required",
        )

    return user


async def require_admin(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Require admin authentication.

    Returns the authenticated admin user.
    Raises 401 if not authenticated.
    Raises 403 if not admin.
    """
    user = await require_auth(request, db)

    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user
