"""Authentication service with password hashing and JWT operations."""

import hashlib
import os
import secrets
import string
from datetime import datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

# Password hashing using bcrypt via pwdlib
pwd_context = PasswordHash((BcryptHasher(),))

# JWT settings (use env vars with defaults)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours default
ACCESS_TOKEN_EXPIRE_REMEMBER_ME_DAYS = 30  # 30 days with remember_me


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: UUID,
    email: str,
    is_admin: bool,
    remember_me: bool = False,
) -> tuple[str, datetime]:
    """Create JWT access token.

    Args:
        user_id: User's UUID
        email: User's email
        is_admin: Whether user has admin role
        remember_me: If True, token expires in 30 days, else 8 hours

    Returns:
        Tuple of (token, expires_at datetime)
    """
    if remember_me:
        expires_delta = timedelta(days=ACCESS_TOKEN_EXPIRE_REMEMBER_ME_DAYS)
    else:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expires_at = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "exp": expires_at,
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expires_at


def verify_token(token: str) -> dict | None:
    """Verify and decode JWT.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict or None if invalid/expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """SHA256 hash of token for storage/lookup.

    Used for session tracking without storing the actual JWT.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_temp_password(length: int = 12) -> str:
    """Generate a secure temporary password.

    Args:
        length: Password length (default 12)

    Returns:
        Random alphanumeric password
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_reset_token() -> str:
    """Generate a secure URL-safe reset token.

    Returns:
        URL-safe token string (32 bytes = ~43 chars)
    """
    return secrets.token_urlsafe(32)
