"""History-related Pydantic schemas for API.

Provides schemas for viewing and filtering validation history.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.schemas.validation import FindingResponse
from src.storage.models import ValidationStatus


class HistoryListItem(BaseModel):
    """Summary item for history list view.

    Combines ValidationResult and Document data for display.
    """

    id: UUID = Field(description="ValidationResult ID")
    document_id: UUID = Field(description="Document ID")
    document_filename: str = Field(description="Original document filename")
    status: ValidationStatus = Field(description="Validation result status")
    created_at: datetime = Field(description="When validation was performed")
    findings_count: int | None = Field(
        default=None, description="Number of findings in this validation"
    )

    model_config = {"from_attributes": True}


class HistoryListResponse(BaseModel):
    """Paginated response for validation history list.

    Supports filtering by:
    - status: Filter by validation status (APPROVED, REJECTED, REVIEW_NEEDED)
    - start_date: Filter validations on or after this date
    - end_date: Filter validations on or before this date
    - document_name: Partial match search on document filename (case-insensitive)

    Filters combine with AND logic.
    """

    items: list[HistoryListItem] = Field(description="Validation history items")
    total: int = Field(description="Total number of matching records")
    page: int = Field(ge=1, description="Current page (1-indexed)")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    has_next: bool = Field(description="Whether there are more pages")
    has_prev: bool = Field(description="Whether there are previous pages")


class DocumentInfo(BaseModel):
    """Document metadata for history detail view."""

    id: UUID
    filename: str
    file_hash: str
    file_size_bytes: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class HistoryDetailResponse(BaseModel):
    """Full validation detail for history view."""

    id: UUID
    document: DocumentInfo
    status: ValidationStatus
    findings: list[FindingResponse]
    validated_at: datetime  # ValidationResult.created_at
    validator_version: str | None  # rule_version
    model_version: str | None
    processing_time_ms: int | None

    # Audit trail info
    findings_count: int
    has_extraction: bool
    has_analysis: bool
