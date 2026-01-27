"""Tests for login and logout endpoints."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.services.auth import hash_password, hash_token
from src.storage.models import User, Session


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    from sqlalchemy import delete, select

    # Clean up any existing test user and their sessions
    result = await db_session.execute(
        select(User).where(User.email == "test@example.com")
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        # Delete sessions first (foreign key constraint)
        await db_session.execute(
            delete(Session).where(Session.user_id == existing_user.id)
        )
        await db_session.execute(
            delete(User).where(User.email == "test@example.com")
        )
        await db_session.commit()

    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password=hash_password("validpass123"),
        is_active=True,
        is_superuser=False,
        failed_login_attempts=0,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def locked_user(db_session: AsyncSession):
    """Create a locked user."""
    from sqlalchemy import delete

    # Clean up any existing locked user
    await db_session.execute(
        delete(User).where(User.email == "locked@example.com")
    )
    await db_session.commit()

    user = User(
        id=uuid4(),
        email="locked@example.com",
        hashed_password=hash_password("validpass123"),
        is_active=True,
        is_superuser=False,
        failed_login_attempts=3,
        locked_until=datetime.utcnow() + timedelta(minutes=30),
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestLogin:
    """Login endpoint tests."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Valid credentials return token."""
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Unknown email returns 401."""
        response = await client.post(
            "/auth/login",
            json={"email": "unknown@example.com", "password": "anypass"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user):
        """Wrong password returns 401."""
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_locked_account(self, client: AsyncClient, locked_user):
        """Locked account returns 403."""
        response = await client.post(
            "/auth/login",
            json={"email": "locked@example.com", "password": "validpass123"},
        )
        assert response.status_code == 403
        assert "locked" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_tracks_failed_attempts(self, client: AsyncClient, test_user, db_session: AsyncSession):
        """Failed attempts are tracked and account locks after 3 failures."""
        # Fail 2 times
        for _ in range(2):
            await client.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "wrong"},
            )

        # On 3rd failure, should lock
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

        # 4th attempt should show locked
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_login_remember_me_extends_expiry(self, client: AsyncClient, test_user):
        """Remember me gives longer token."""
        # Without remember_me
        response1 = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "validpass123", "remember_me": False},
        )
        expires1 = response1.json()["expires_in"]

        # With remember_me
        response2 = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "validpass123", "remember_me": True},
        )
        expires2 = response2.json()["expires_in"]

        # remember_me should be significantly longer (30 days vs 8 hours)
        assert expires2 > expires1 * 10  # 30 days >> 8 hours

    @pytest.mark.asyncio
    async def test_login_creates_session(self, client: AsyncClient, test_user, db_session: AsyncSession):
        """Login creates session record."""
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        assert response.status_code == 200

        # Session should exist (verify via sessions endpoint)
        token = response.json()["access_token"]
        sessions_response = await client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sessions_response.status_code == 200
        sessions = sessions_response.json()
        assert len(sessions) >= 1


class TestLogout:
    """Logout endpoint tests."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, test_user):
        """Valid token logout returns 204."""
        # Login first
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        token = login_response.json()["access_token"]

        # Logout
        response = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_logout_no_token(self, client: AsyncClient):
        """Missing token returns 401."""
        response = await client.post("/auth/logout")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, client: AsyncClient):
        """Invalid token returns 401."""
        response = await client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_revokes_session(self, client: AsyncClient, test_user):
        """Logout revokes the session, second logout fails."""
        # Login
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        token = login_response.json()["access_token"]

        # First logout succeeds
        response1 = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 204

        # Second logout with same token fails (session revoked)
        response2 = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should be 401 since session is revoked
        assert response2.status_code == 401


@pytest.fixture
async def session_test_user(db_session: AsyncSession):
    """Create a dedicated user for session limit tests."""
    from sqlalchemy import delete, select

    # Clean up any existing user and their sessions
    result = await db_session.execute(
        select(User).where(User.email == "sessiontest@example.com")
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        await db_session.execute(
            delete(Session).where(Session.user_id == existing_user.id)
        )
        await db_session.execute(
            delete(User).where(User.email == "sessiontest@example.com")
        )
        await db_session.commit()

    user = User(
        id=uuid4(),
        email="sessiontest@example.com",
        hashed_password=hash_password("validpass123"),
        is_active=True,
        is_superuser=False,
        failed_login_attempts=0,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    yield user

    # Cleanup after test - remove all sessions for this user
    await db_session.execute(
        delete(Session).where(Session.user_id == user.id)
    )
    await db_session.execute(
        delete(User).where(User.id == user.id)
    )
    await db_session.commit()


class TestSessionLimit:
    """Concurrent session limit tests."""

    @pytest.mark.asyncio
    async def test_max_three_sessions(self, client: AsyncClient, session_test_user):
        """Fourth login revokes oldest session."""
        tokens = []
        for i in range(4):
            response = await client.post(
                "/auth/login",
                json={"email": "sessiontest@example.com", "password": "validpass123"},
            )
            assert response.status_code == 200
            tokens.append(response.json()["access_token"])

        # Check sessions with newest token
        sessions_response = await client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {tokens[-1]}"},
        )
        assert sessions_response.status_code == 200
        active_sessions = sessions_response.json()
        assert len(active_sessions) == 3  # Max 3 concurrent

        # Oldest token should be revoked
        # Trying to use it for logout should fail
        logout_response = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {tokens[0]}"},
        )
        assert logout_response.status_code == 401  # Session was revoked
