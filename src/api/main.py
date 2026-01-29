"""AuditEng V2 - FastAPI Application."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import admin, auth, documents, health, history, validate
from src.storage.database import init_db


async def ensure_admin_exists():
    """Create default admin if no admin exists."""
    from sqlalchemy import select, func
    from src.storage.database import async_session
    from src.storage.models import User
    from src.domain.services.auth import hash_password
    from uuid import uuid4

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@auditeng.com")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_password:
        print("ADMIN_PASSWORD not set, skipping admin creation")
        return

    async with async_session() as db:
        # Check if any admin exists
        result = await db.execute(
            select(func.count()).select_from(User).where(User.is_superuser == True)
        )
        admin_count = result.scalar()

        if admin_count > 0:
            print(f"Admin user already exists ({admin_count} admins)")
            return

        # Create admin
        user = User(
            id=uuid4(),
            email=admin_email,
            hashed_password=hash_password(admin_password),
            is_active=True,
            is_superuser=True,
            must_change_password=False,
            failed_login_attempts=0,
        )
        db.add(user)
        await db.commit()
        print(f"Created admin user: {admin_email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    await ensure_admin_exists()
    yield
    # Shutdown


app = FastAPI(
    title="AuditEng V2",
    description="Automated validation system for electrical commissioning reports",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration for frontend
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:3000",
    "https://frontend-production-888b.up.railway.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(documents.router, tags=["documents"])
app.include_router(validate.router, prefix="/documents", tags=["validation"])
app.include_router(history.router)
