"""Validation evidence schemas for AuditEng V2.

Provides data structures for validation findings and their evidence.
Used to track what was validated, what was found, and why decisions were made.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.domain.schemas.extraction import FieldLocation
from src.storage.models import ValidationStatus


class FindingSeverity(str, Enum):
    """Severity levels for validation findings.

    Determines how the finding affects the overall validation status:
    - ERROR: Causes REJECTED status (critical failure)
    - WARNING: Causes REVIEW_NEEDED status (needs human review)
    - INFO: Logged but doesn't affect status (informational)
    """

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class Finding(BaseModel):
    """A single validation finding.

    Represents one check result with full context for audit trail.
    Contains what was checked, what was found, and what was expected.
    """

    rule_id: str = Field(
        description="Validation rule identifier, e.g., 'VAL-01', 'VAL-02'"
    )
    severity: FindingSeverity = Field(
        description="Severity level determining impact on validation status"
    )
    message: str = Field(description="Human-readable description of the finding")
    field_name: str = Field(description="Which field was checked")
    found_value: str | None = Field(
        default=None, description="What was found in the document"
    )
    expected_value: str | None = Field(
        default=None, description="What was expected, if applicable"
    )
    location: FieldLocation | None = Field(
        default=None, description="Page and bounding box reference from extraction"
    )


class ValidationEvidence(BaseModel):
    """Complete validation evidence for a document.

    Aggregates all findings from validation with metadata for audit trail.
    """

    document_id: str = Field(description="Document being validated")
    findings: list[Finding] = Field(
        default_factory=list, description="All validation findings"
    )
    checked_at: datetime = Field(description="When validation was performed")
    validator_version: str = Field(
        description="Version of validator for audit trail, e.g., '1.0.0'"
    )


def compute_status(findings: list[Finding]) -> ValidationStatus:
    """Compute overall validation status from findings.

    Priority (highest to lowest):
    1. Any ERROR finding -> REJECTED
    2. Any WARNING finding -> REVIEW_NEEDED
    3. INFO only or no findings -> APPROVED

    Args:
        findings: List of validation findings to evaluate.

    Returns:
        ValidationStatus based on finding severities.
    """
    has_error = any(f.severity == FindingSeverity.ERROR for f in findings)
    has_warning = any(f.severity == FindingSeverity.WARNING for f in findings)

    if has_error:
        return ValidationStatus.REJECTED
    if has_warning:
        return ValidationStatus.REVIEW_NEEDED
    return ValidationStatus.APPROVED
