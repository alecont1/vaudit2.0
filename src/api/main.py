"""AuditEng V2 - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import admin, auth, documents, health, history, validate
from src.storage.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown (nothing to clean up for SQLite)


app = FastAPI(
    title="AuditEng V2",
    description="Automated validation system for electrical commissioning reports",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(documents.router, tags=["documents"])
app.include_router(validate.router, prefix="/documents", tags=["validation"])
app.include_router(history.router)
