"""Document-related Pydantic schemas for API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    """Schema for document upload metadata."""

    filename: str


class DocumentRead(BaseModel):
    """Schema for reading document data."""

    id: UUID
    filename: str
    file_hash: str
    file_size_bytes: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
