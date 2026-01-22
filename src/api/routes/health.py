"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return API health status.

    Used by load balancers and monitoring systems to verify
    the service is running and responsive.
    """
    return HealthResponse(status="ok", version="0.1.0")
