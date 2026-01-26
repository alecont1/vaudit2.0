"""Validation-related Pydantic schemas for API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.schemas.evidence import Finding
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


# --- API Response schemas for validate endpoint ---


class LocationResponse(BaseModel):
    """API representation of field location.

    Simplified from internal FieldLocation for API consumption.
    """

    page: int = Field(ge=0, description="Zero-indexed page number")
    bbox: dict[str, float] | None = Field(
        default=None, description="Bounding box as {left, top, right, bottom}"
    )


class FindingResponse(BaseModel):
    """API representation of a validation finding.

    Flattened structure for easier API consumption.
    Location is extracted to top-level page/bbox fields.
    """

    rule_id: str = Field(description="Validation rule identifier, e.g., 'VAL-01'")
    severity: str = Field(description="Severity level: ERROR, WARNING, or INFO")
    message: str = Field(description="Human-readable description of the finding")
    field_name: str = Field(description="Which field was checked")
    found_value: str | None = Field(
        default=None, description="What was found in the document"
    )
    expected_value: str | None = Field(
        default=None, description="What was expected, if applicable"
    )
    page: int | None = Field(default=None, description="Page number where field found")
    bbox: dict[str, float] | None = Field(
        default=None, description="Bounding box coordinates"
    )


class ValidationResponse(BaseModel):
    """Full validation result for API response.

    Contains the overall status and all findings with evidence.
    """

    document_id: UUID = Field(description="Document that was validated")
    status: ValidationStatus = Field(description="Overall validation status")
    findings: list[FindingResponse] = Field(
        default_factory=list, description="All validation findings with evidence"
    )
    checked_at: datetime = Field(description="When validation was performed")
    validator_version: str = Field(
        description="Version of validator rules for audit trail"
    )


def finding_to_response(finding: Finding) -> FindingResponse:
    """Convert internal Finding to API-safe FindingResponse.

    Extracts page and bbox from location if present, flattening
    the structure for easier API consumption.

    Args:
        finding: Internal Finding object from validators.

    Returns:
        FindingResponse suitable for API response.
    """
    page: int | None = None
    bbox: dict[str, float] | None = None

    if finding.location is not None:
        page = finding.location.page
        if finding.location.bbox is not None:
            bbox = {
                "left": finding.location.bbox.left,
                "top": finding.location.bbox.top,
                "right": finding.location.bbox.right,
                "bottom": finding.location.bbox.bottom,
            }

    return FindingResponse(
        rule_id=finding.rule_id,
        severity=finding.severity.value,  # Convert enum to string
        message=finding.message,
        field_name=finding.field_name,
        found_value=finding.found_value,
        expected_value=finding.expected_value,
        page=page,
        bbox=bbox,
    )
