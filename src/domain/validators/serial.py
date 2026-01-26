"""Serial number cross-validation for AuditEng V2.

Validates serial number consistency across multiple document locations.
Implements VAL-02 validation rule.

Serial numbers should match across report header, photo metadata, and certificate.
Mismatches indicate potential copy-paste errors or document tampering.
"""

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import CalibrationInfo, ExtractionResult, ExtractedField


def validate_serial_consistency(
    serial_numbers: list[ExtractedField],
    rule_id: str = "VAL-02",
) -> list[Finding]:
    """Validate serial number consistency across multiple locations.

    Compares all serial numbers found in the document to ensure they match.
    Normalization is applied (strip whitespace, uppercase) since serial numbers
    are case-insensitive.

    Args:
        serial_numbers: List of serial number fields extracted from document.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings:
        - INFO if check skipped (0-1 serial numbers)
        - INFO if all serial numbers match
        - ERROR if any serial numbers mismatch
    """
    findings: list[Finding] = []

    # Case 1: Insufficient data for cross-validation
    if len(serial_numbers) < 2:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.INFO,
                message="Serial number consistency check skipped (insufficient data)",
                field_name="serial_number",
                found_value=serial_numbers[0].value if serial_numbers else None,
                expected_value=None,
                location=serial_numbers[0].location if serial_numbers else None,
            )
        )
        return findings

    # Extract and normalize values, filtering out None
    normalized_serials: list[tuple[str, ExtractedField]] = []
    for field in serial_numbers:
        if field.value is not None:
            normalized = field.value.strip().upper()
            normalized_serials.append((normalized, field))

    # If all values were None, skip check
    if len(normalized_serials) < 2:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.INFO,
                message="Serial number consistency check skipped (insufficient valid values)",
                field_name="serial_number",
                found_value=None,
                expected_value=None,
                location=None,
            )
        )
        return findings

    # Get unique normalized values
    unique_values = set(norm for norm, _ in normalized_serials)

    # Case 2: All serial numbers match
    if len(unique_values) == 1:
        serial_value = next(iter(unique_values))
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.INFO,
                message=f"Serial numbers consistent: {serial_value} (found in {len(normalized_serials)} locations)",
                field_name="serial_number",
                found_value=serial_value,
                expected_value=None,
                location=normalized_serials[0][1].location,
            )
        )
        return findings

    # Case 3: Serial number mismatch detected
    unique_values_str = ", ".join(sorted(unique_values))
    findings.append(
        Finding(
            rule_id=rule_id,
            severity=FindingSeverity.ERROR,
            message="Serial number mismatch detected",
            field_name="serial_number",
            found_value=unique_values_str,
            expected_value="All serial numbers should match",
            location=normalized_serials[0][1].location,
        )
    )

    # Add supplementary findings for each serial number location
    for norm_value, field in normalized_serials:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.INFO,
                message=f"Serial number '{norm_value}' found at this location",
                field_name="serial_number",
                found_value=norm_value,
                expected_value=None,
                location=field.location,
            )
        )

    return findings


def collect_serial_numbers(extraction: ExtractionResult) -> list[ExtractedField]:
    """Collect all serial numbers from an extraction result.

    Extracts serial_number fields from all CalibrationInfo objects
    in the extraction result.

    Args:
        extraction: Complete extraction result for a document.

    Returns:
        List of ExtractedField objects containing serial numbers.
        Empty list if no calibrations or no serial numbers found.
    """
    serial_numbers: list[ExtractedField] = []

    for calibration in extraction.calibrations:
        if calibration.serial_number is not None:
            serial_numbers.append(calibration.serial_number)

    return serial_numbers
