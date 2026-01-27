"""Admin endpoints for user management."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.schemas.auth import UserCreateAdmin
from src.domain.schemas.user import UserRead
from src.domain.services.auth import (
    verify_token,
    hash_password,
    generate_temp_password,
)
from src.domain.services.email import send_temp_password_email
from src.storage.database import get_session
from src.storage.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


class UserCreateResponse(BaseModel):
    """Response when creating a user (includes temp password for display)."""

    user: UserRead
    temp_password: str


class UserListResponse(BaseModel):
    """Response for listing users."""

    users: list[UserRead]
    total: int


async def require_admin(request: Request, db: AsyncSession) -> User:
    """Dependency to require admin authentication.

    Returns the admin user if valid, raises 401/403 otherwise.
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

    if not payload.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    user_id = UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user


@router.post("/users", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreateAdmin,
    db: AsyncSession = Depends(get_session),
) -> UserCreateResponse:
    """Create a new user account (admin only).

    Generates a temporary password that user must change on first login.
    Returns the temp password for display AND sends it via email.
    """
    # Verify admin
    await require_admin(request, db)

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Generate temp password
    temp_password = generate_temp_password()

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=hash_password(temp_password),
        is_active=True,
        is_superuser=(user_data.role == "admin"),
        must_change_password=True,  # Must change temp password
        failed_login_attempts=0,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send email with temp password
    await send_temp_password_email(user.email, temp_password)

    return UserCreateResponse(
        user=UserRead.model_validate(user),
        temp_password=temp_password,
    )


@router.post("/users/{user_id}/unlock", status_code=status.HTTP_204_NO_CONTENT)
async def unlock_user(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """Unlock a locked user account (admin only).

    Clears failed_login_attempts and locked_until.
    """
    # Verify admin
    await require_admin(request, db)

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Unlock
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = datetime.utcnow()
    await db.commit()

    return None  # 204 No Content


@router.get("/users", response_model=UserListResponse)
async def list_users(
    request: Request,
    db: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 50,
) -> UserListResponse:
    """List all users (admin only)."""
    # Verify admin
    await require_admin(request, db)

    # Get users
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    # Get total count
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar()

    return UserListResponse(
        users=[UserRead.model_validate(u) for u in users],
        total=total or 0,
    )


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> UserRead:
    """Get user details (admin only)."""
    # Verify admin
    await require_admin(request, db)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserRead.model_validate(user)
