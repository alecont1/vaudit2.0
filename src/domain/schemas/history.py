"""History-related Pydantic schemas for API.

Provides schemas for viewing and filtering validation history.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

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
