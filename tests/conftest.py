"""Pytest configuration and fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.storage.database import async_session, init_db


@pytest.fixture(scope="session", autouse=True)
async def initialize_database():
    """Initialize database before all tests."""
    await init_db()


@pytest.fixture
async def client():
    """Async test client for FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def db_session():
    """Async database session for tests."""
    async with async_session() as session:
        yield session
