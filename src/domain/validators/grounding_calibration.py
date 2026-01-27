"""Grounding test calibration validation.

Validates grounding meter calibration certificate against test date.
Implements GROUND-01 validation rule.
"""

from datetime import date

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import GroundingData
from src.domain.validators.calibration import validate_calibration


def validate_grounding_calibration(
    grounding: GroundingData,
    test_date: date,
    rule_id: str = "GROUND-01",
) -> list[Finding]:
    """Validate grounding meter calibration against test date.

    Delegates to validate_calibration with GROUND-01 rule_id.
    Returns WARNING finding if no calibration info present (zero false rejections).

    Args:
        grounding: Grounding test data containing calibration info.
        test_date: Date when the grounding test was performed.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings. Contains:
        - WARNING if calibration info missing (manual review required)
        - Results from validate_calibration if calibration present
    """
    if grounding.calibration is None:
        return [
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Grounding meter calibration information missing - manual review required",
                field_name="grounding_calibration",
                found_value=None,
                expected_value=None,
                location=None,
            )
        ]
    return validate_calibration(grounding.calibration, test_date, rule_id)
