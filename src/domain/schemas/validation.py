"""Validation-related Pydantic schemas for API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.storage.models import ValidationStatus


class ValidationResultRead(BaseModel):
    """Schema for reading validation results."""

    id: UUID
    document_id: UUID
    status: ValidationStatus
    confidence: float | None
    findings: list[dict[str, Any]] | None = None  # Parsed from JSON
    created_at: datetime

    model_config = {"from_attributes": True}


class ValidationSummary(BaseModel):
    """Brief validation summary for listings."""

    id: UUID
    document_filename: str
    status: ValidationStatus
    created_at: datetime
