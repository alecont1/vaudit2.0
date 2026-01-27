"""Tests for admin user management endpoints."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.services.auth import hash_password
from src.storage.models import User, Session


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create an admin user for testing."""
    # Clean up any existing admin user and their sessions
    result = await db_session.execute(
        select(User).where(User.email == "admin@example.com")
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db_session.execute(
            delete(Session).where(Session.user_id == existing.id)
        )
        await db_session.execute(
            delete(User).where(User.email == "admin@example.com")
        )
        await db_session.commit()

    user = User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password=hash_password("adminpass123"),
        is_active=True,
        is_superuser=True,  # Admin!
        failed_login_attempts=0,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def regular_user(db_session: AsyncSession):
    """Create a regular (non-admin) user for testing."""
    # Clean up any existing user
    result = await db_session.execute(
        select(User).where(User.email == "user@example.com")
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db_session.execute(
            delete(Session).where(Session.user_id == existing.id)
        )
        await db_session.execute(
            delete(User).where(User.email == "user@example.com")
        )
        await db_session.commit()

    user = User(
        id=uuid4(),
        email="user@example.com",
        hashed_password=hash_password("userpass123"),
        is_active=True,
        is_superuser=False,  # Not admin
        failed_login_attempts=0,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def locked_user(db_session: AsyncSession):
    """Create a locked user for testing."""
    # Clean up any existing locked user
    result = await db_session.execute(
        select(User).where(User.email == "locked@example.com")
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db_session.execute(
            delete(Session).where(Session.user_id == existing.id)
        )
        await db_session.execute(
            delete(User).where(User.email == "locked@example.com")
        )
        await db_session.commit()

    user = User(
        id=uuid4(),
        email="locked@example.com",
        hashed_password=hash_password("lockedpass123"),
        is_active=True,
        is_superuser=False,
        failed_login_attempts=3,
        locked_until=datetime.utcnow() + timedelta(hours=1),
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def get_admin_token(client: AsyncClient) -> str:
    """Helper to get admin auth token."""
    response = await client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    return response.json()["access_token"]


async def get_user_token(client: AsyncClient) -> str:
    """Helper to get regular user auth token."""
    response = await client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "userpass123"},
    )
    return response.json()["access_token"]


class TestCreateUser:
    """Tests for POST /admin/users."""

    @pytest.mark.asyncio
    async def test_admin_can_create_user(self, client: AsyncClient, admin_user):
        """Admin can create new user account."""
        token = await get_admin_token(client)

        response = await client.post(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "newuser@example.com", "role": "user"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "newuser@example.com"
        assert "temp_password" in data
        assert len(data["temp_password"]) >= 12

    @pytest.mark.asyncio
    async def test_admin_can_create_admin(self, client: AsyncClient, admin_user):
        """Admin can create another admin user."""
        token = await get_admin_token(client)

        response = await client.post(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "newadmin@example.com", "role": "admin"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_regular_user_cannot_create(self, client: AsyncClient, admin_user, regular_user):
        """Non-admin cannot create users - returns 403."""
        token = await get_user_token(client)

        response = await client.post(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "another@example.com", "role": "user"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_no_token_cannot_create(self, client: AsyncClient):
        """Missing token returns 401."""
        response = await client.post(
            "/admin/users",
            json={"email": "another@example.com", "role": "user"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self, client: AsyncClient, admin_user, regular_user):
        """Cannot create user with existing email."""
        token = await get_admin_token(client)

        response = await client.post(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "user@example.com", "role": "user"},  # Already exists
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_created_user_can_login_with_temp_password(self, client: AsyncClient, admin_user):
        """Newly created user can login with temp password."""
        token = await get_admin_token(client)

        # Create user
        create_response = await client.post(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "mustchange@example.com", "role": "user"},
        )
        assert create_response.status_code == 201
        temp_password = create_response.json()["temp_password"]

        # New user can login
        login_response = await client.post(
            "/auth/login",
            json={"email": "mustchange@example.com", "password": temp_password},
        )
        assert login_response.status_code == 200


class TestUnlockUser:
    """Tests for POST /admin/users/{id}/unlock."""

    @pytest.mark.asyncio
    async def test_admin_can_unlock_user(self, client: AsyncClient, admin_user, locked_user):
        """Admin can unlock a locked user."""
        token = await get_admin_token(client)

        response = await client.post(
            f"/admin/users/{locked_user.id}/unlock",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # User can now login
        login_response = await client.post(
            "/auth/login",
            json={"email": "locked@example.com", "password": "lockedpass123"},
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_regular_user_cannot_unlock(self, client: AsyncClient, admin_user, regular_user, locked_user):
        """Non-admin cannot unlock users - returns 403."""
        token = await get_user_token(client)

        response = await client.post(
            f"/admin/users/{locked_user.id}/unlock",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unlock_nonexistent_user(self, client: AsyncClient, admin_user):
        """Unlocking non-existent user returns 404."""
        token = await get_admin_token(client)
        fake_id = uuid4()

        response = await client.post(
            f"/admin/users/{fake_id}/unlock",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


class TestListUsers:
    """Tests for GET /admin/users."""

    @pytest.mark.asyncio
    async def test_admin_can_list_users(self, client: AsyncClient, admin_user, regular_user):
        """Admin can list all users."""
        token = await get_admin_token(client)

        response = await client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert data["total"] >= 2  # At least admin and regular user

    @pytest.mark.asyncio
    async def test_regular_user_cannot_list(self, client: AsyncClient, admin_user, regular_user):
        """Non-admin cannot list users - returns 403."""
        token = await get_user_token(client)

        response = await client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


class TestGetUser:
    """Tests for GET /admin/users/{id}."""

    @pytest.mark.asyncio
    async def test_admin_can_get_user(self, client: AsyncClient, admin_user, regular_user):
        """Admin can get user details."""
        token = await get_admin_token(client)

        response = await client.get(
            f"/admin/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, client: AsyncClient, admin_user):
        """Getting non-existent user returns 404."""
        token = await get_admin_token(client)
        fake_id = uuid4()

        response = await client.get(
            f"/admin/users/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
