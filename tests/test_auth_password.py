"""Tests for password management endpoints."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.services.auth import hash_password, generate_reset_token, hash_token
from src.storage.models import User, PasswordResetToken


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    # Use unique email with timestamp to avoid conflicts
    from time import time
    from sqlalchemy import delete
    from src.storage.models import Session, PasswordResetToken

    user = User(
        id=uuid4(),
        email=f"test{int(time()*1000000)}@example.com",
        hashed_password=hash_password("currentpass123"),
        is_active=True,
        is_superuser=False,
        failed_login_attempts=0,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    # Cleanup after test - delete related records first
    await db_session.execute(delete(Session).where(Session.user_id == user.id))
    await db_session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    await db_session.delete(user)
    await db_session.commit()


@pytest.fixture
async def user_must_change(db_session: AsyncSession):
    """Create a user who must change password."""
    from time import time
    from sqlalchemy import delete
    from src.storage.models import Session, PasswordResetToken

    user = User(
        id=uuid4(),
        email=f"mustchange{int(time()*1000000)}@example.com",
        hashed_password=hash_password("temppass123"),
        is_active=True,
        is_superuser=False,
        failed_login_attempts=0,
        must_change_password=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    # Cleanup after test - delete related records first
    await db_session.execute(delete(Session).where(Session.user_id == user.id))
    await db_session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    await db_session.delete(user)
    await db_session.commit()


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    """Helper to get auth token."""
    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()["access_token"]


class TestChangePassword:
    """Password change endpoint tests."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, test_user):
        """Valid current password allows change."""
        token = await get_token(client, test_user.email, "currentpass123")

        response = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "currentpass123",
                "new_password": "newpass12345",
            },
        )
        assert response.status_code == 204

        # Can login with new password
        login_response = await client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "newpass12345"},
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, test_user):
        """Wrong current password returns 400."""
        token = await get_token(client, test_user.email, "currentpass123")

        response = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrongpassword",
                "new_password": "newpass12345",
            },
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_no_token(self, client: AsyncClient):
        """Missing token returns 401."""
        response = await client.post(
            "/auth/change-password",
            json={
                "current_password": "anything",
                "new_password": "newpass12345",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_change_password_clears_must_change_flag(self, client: AsyncClient, user_must_change):
        """Changing password clears must_change_password flag."""
        token = await get_token(client, user_must_change.email, "temppass123")

        response = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "temppass123",
                "new_password": "permanentpass123",
            },
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_change_password_too_short(self, client: AsyncClient, test_user):
        """Password under 8 chars rejected."""
        token = await get_token(client, test_user.email, "currentpass123")

        response = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "currentpass123",
                "new_password": "short",  # Less than 8 chars
            },
        )
        assert response.status_code == 422  # Validation error


class TestForgotPassword:
    """Forgot password endpoint tests."""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_email(self, client: AsyncClient, test_user):
        """Existing email returns 202 (accepted)."""
        response = await client.post(
            "/auth/forgot-password",
            json={"email": test_user.email},
        )
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_forgot_password_unknown_email(self, client: AsyncClient):
        """Unknown email also returns 202 (prevent enumeration)."""
        response = await client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 202


class TestResetPassword:
    """Password reset endpoint tests."""

    @pytest.fixture
    async def reset_token(self, test_user, db_session: AsyncSession):
        """Create a valid reset token for test user."""
        raw_token = generate_reset_token()
        token_record = PasswordResetToken(
            user_id=test_user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
        db_session.add(token_record)
        await db_session.commit()
        return raw_token

    @pytest.fixture
    async def expired_token(self, test_user, db_session: AsyncSession):
        """Create an expired reset token."""
        raw_token = generate_reset_token()
        token_record = PasswordResetToken(
            user_id=test_user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() - timedelta(minutes=1),  # Already expired
        )
        db_session.add(token_record)
        await db_session.commit()
        return raw_token

    @pytest.fixture
    async def used_token(self, test_user, db_session: AsyncSession):
        """Create an already-used reset token."""
        raw_token = generate_reset_token()
        token_record = PasswordResetToken(
            user_id=test_user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            used_at=datetime.utcnow(),  # Already used
        )
        db_session.add(token_record)
        await db_session.commit()
        return raw_token

    @pytest.mark.asyncio
    async def test_reset_password_success(self, client: AsyncClient, test_user, reset_token):
        """Valid token allows password reset."""
        response = await client.post(
            "/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "resetpass123",
            },
        )
        assert response.status_code == 204

        # Can login with new password
        login_response = await client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "resetpass123"},
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, client: AsyncClient):
        """Invalid token returns 400."""
        response = await client.post(
            "/auth/reset-password",
            json={
                "token": "invalid-token-string",
                "new_password": "newpass12345",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self, client: AsyncClient, test_user, expired_token):
        """Expired token returns 400."""
        response = await client.post(
            "/auth/reset-password",
            json={
                "token": expired_token,
                "new_password": "newpass12345",
            },
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_reset_password_used_token(self, client: AsyncClient, test_user, used_token):
        """Already-used token returns 400."""
        response = await client.post(
            "/auth/reset-password",
            json={
                "token": used_token,
                "new_password": "newpass12345",
            },
        )
        assert response.status_code == 400
        assert "used" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_reset_password_clears_lockout(self, client: AsyncClient, db_session: AsyncSession, test_user, reset_token):
        """Password reset clears account lockout."""
        # First lock the account
        test_user.failed_login_attempts = 3
        test_user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        db_session.add(test_user)
        await db_session.commit()

        response = await client.post(
            "/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "resetpass123",
            },
        )
        assert response.status_code == 204

        # Should be able to login now (lockout cleared)
        login_response = await client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "resetpass123"},
        )
        assert login_response.status_code == 200
