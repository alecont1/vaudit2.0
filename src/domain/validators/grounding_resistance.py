"""Grounding resistance validation.

Validates grounding resistance values against technical standards.
Implements GROUND-02 validation rule.

Thresholds (per ABNT NBR 5419 / IEEE 142):
- > 10 ohms: Critical failure (REJECTED)
- > 5 ohms: Borderline (REVIEW_NEEDED)
- <= 5 ohms: Acceptable (APPROVED)

Core principle: Zero false rejections. When uncertain (missing/unparseable value),
use WARNING (REVIEW_NEEDED) instead of ERROR (REJECTED).
"""

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import GroundingData

# Threshold constants (in ohms)
RESISTANCE_WARNING_THRESHOLD = 5.0  # > 5 ohms needs review
RESISTANCE_ERROR_THRESHOLD = 10.0  # > 10 ohms is failure


def validate_grounding_resistance(
    grounding: GroundingData,
    rule_id: str = "GROUND-02",
) -> list[Finding]:
    """Validate grounding resistance against technical standard limits.

    Evaluates grounding resistance measurements against threshold values
    defined by ABNT NBR 5419 and IEEE 142 standards.

    Args:
        grounding: GroundingData containing resistance measurement.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings based on resistance thresholds:
        - ERROR if resistance > 10 ohms (critical failure)
        - WARNING if 5 ohms < resistance <= 10 ohms (borderline)
        - INFO if resistance <= 5 ohms (acceptable)
        - WARNING if value is missing/unparseable/negative
    """
    findings: list[Finding] = []

    # Case 1: Missing resistance field entirely
    if grounding.resistance_value is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Grounding resistance value not found - manual review required",
                field_name="grounding_resistance",
                found_value=None,
                expected_value="numeric resistance in ohms",
                location=None,
            )
        )
        return findings

    # Case 2: Field exists but value is None or empty
    raw_value = grounding.resistance_value.value
    if raw_value is None or raw_value.strip() == "":
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Grounding resistance value is missing or empty - manual review required",
                field_name="grounding_resistance",
                found_value=raw_value,
                expected_value="numeric resistance in ohms",
                location=grounding.resistance_value.location,
            )
        )
        return findings

    # Case 3: Try to parse as float
    try:
        resistance = float(raw_value)
    except (ValueError, TypeError):
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Could not parse grounding resistance '{raw_value}' as numeric value - manual review required",
                field_name="grounding_resistance",
                found_value=raw_value,
                expected_value="numeric resistance in ohms",
                location=grounding.resistance_value.location,
            )
        )
        return findings

    # Case 4: Negative value (invalid measurement)
    if resistance < 0:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Grounding resistance {resistance} ohms is negative (invalid measurement) - manual review required",
                field_name="grounding_resistance",
                found_value=f"{resistance} ohms",
                expected_value=">= 0 ohms",
                location=grounding.resistance_value.location,
            )
        )
        return findings

    # Case 5: Evaluate against thresholds
    if resistance > RESISTANCE_ERROR_THRESHOLD:
        # Critical failure - ERROR
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.ERROR,
                message=f"Grounding resistance {resistance} ohms exceeds maximum of {RESISTANCE_ERROR_THRESHOLD} ohms",
                field_name="grounding_resistance",
                found_value=f"{resistance} ohms",
                expected_value=f"<= {RESISTANCE_ERROR_THRESHOLD} ohms",
                location=grounding.resistance_value.location,
            )
        )
    elif resistance > RESISTANCE_WARNING_THRESHOLD:
        # Borderline - WARNING
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Grounding resistance {resistance} ohms is borderline - review recommended (threshold: {RESISTANCE_WARNING_THRESHOLD} ohms)",
                field_name="grounding_resistance",
                found_value=f"{resistance} ohms",
                expected_value=f"<= {RESISTANCE_WARNING_THRESHOLD} ohms",
                location=grounding.resistance_value.location,
            )
        )
    else:
        # Acceptable - INFO
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.INFO,
                message=f"Grounding resistance {resistance} ohms within acceptable range (<= {RESISTANCE_WARNING_THRESHOLD} ohms)",
                field_name="grounding_resistance",
                found_value=f"{resistance} ohms",
                expected_value=f"<= {RESISTANCE_WARNING_THRESHOLD} ohms",
                location=grounding.resistance_value.location,
            )
        )

    return findings
