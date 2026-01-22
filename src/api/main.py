"""AuditEng V2 - FastAPI Application."""

from fastapi import FastAPI

from src.api.routes import health

app = FastAPI(
    title="AuditEng V2",
    description="Automated validation system for electrical commissioning reports",
    version="0.1.0",
)

app.include_router(health.router, tags=["health"])


@app.on_event("startup")
async def startup():
    """Initialize resources on startup."""
    # Database initialization will be added in Plan 02
    pass
