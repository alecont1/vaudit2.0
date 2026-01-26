"""Calibration certificate validation for AuditEng V2.

Validates calibration certificate expiration dates against test dates.
Implements VAL-01 validation rule.

Core principle: Zero false rejections. When uncertain (missing/unparseable date),
use WARNING (REVIEW_NEEDED) instead of ERROR (REJECTED).
"""

from datetime import date

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import CalibrationInfo
from src.domain.validators.date_parser import parse_date


def validate_calibration(
    calibration: CalibrationInfo,
    test_date: date,
    rule_id: str = "VAL-01",
) -> list[Finding]:
    """Validate calibration certificate expiration against test date.

    Checks if the calibration certificate was valid at the time the test
    was performed. Expired certificates result in ERROR findings, while
    missing or unparseable dates result in WARNING findings for human review.

    Args:
        calibration: Extracted calibration information from the document.
        test_date: Date when the test was performed.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings. Always contains exactly one finding:
        - ERROR if certificate was expired at test time
        - INFO if certificate was valid at test time
        - WARNING if expiration date is missing or unparseable
    """
    findings: list[Finding] = []

    # Case 1: Missing expiration date field
    if calibration.expiration_date is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Missing calibration expiration date - manual review required",
                field_name="expiration_date",
                found_value=None,
                expected_value=None,
                location=None,
            )
        )
        return findings

    # Case 2: Expiration date field exists but value is None
    if calibration.expiration_date.value is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Missing calibration expiration date - manual review required",
                field_name="expiration_date",
                found_value=None,
                expected_value=None,
                location=calibration.expiration_date.location,
            )
        )
        return findings

    # Extract value and location
    raw_value = calibration.expiration_date.value
    location = calibration.expiration_date.location

    # Case 3: Parse the date
    parsed_expiration = parse_date(raw_value)

    if parsed_expiration is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Could not parse expiration date '{raw_value}' - manual review required",
                field_name="expiration_date",
                found_value=raw_value,
                expected_value=None,
                location=location,
            )
        )
        return findings

    # Case 4: Compare dates
    if parsed_expiration < test_date:
        # Expired certificate - ERROR
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.ERROR,
                message=f"Calibration expired on {parsed_expiration}, test performed on {test_date}",
                field_name="expiration_date",
                found_value=str(parsed_expiration),
                expected_value=f">= {test_date}",
                location=location,
            )
        )
    else:
        # Valid certificate - INFO
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.INFO,
                message=f"Calibration valid until {parsed_expiration}",
                field_name="expiration_date",
                found_value=str(parsed_expiration),
                expected_value=None,
                location=location,
            )
        )

    return findings
