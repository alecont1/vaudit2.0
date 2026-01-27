"""Pytest configuration and fixtures."""

import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from src.api.main import app
from src.storage import database

# Use a test-specific database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./data/test_auditeng.db"

# Create test engine and session factory
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
test_async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Set up test database before all tests and clean up after."""
    # Import models to ensure they're registered
    from src.storage import models  # noqa: F401

    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Override the production database with test database
    database.async_session = test_async_session
    database.engine = test_engine

    yield

    # Clean up: drop all tables after tests
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    # Note: Don't remove the database file here as it may still be in use
    # The file will be cleaned up on next test run when tables are recreated


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
    async with test_async_session() as session:
        yield session
