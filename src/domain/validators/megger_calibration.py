"""Megger test calibration validation.

Validates megger (insulation resistance tester) calibration certificate against test date.
Implements MEGGER-01 validation rule.
"""

from datetime import date

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import MeggerData
from src.domain.validators.calibration import validate_calibration


def validate_megger_calibration(
    megger: MeggerData,
    test_date: date,
    rule_id: str = "MEGGER-01",
) -> list[Finding]:
    """Validate megger calibration against test date.

    Delegates to validate_calibration with MEGGER-01 rule_id.
    Returns WARNING finding if no calibration info present (zero false rejections).

    Args:
        megger: Megger test data containing calibration info.
        test_date: Date when the megger test was performed.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings. Contains:
        - WARNING if calibration info missing (manual review required)
        - Results from validate_calibration if calibration present
    """
    if megger.calibration is None:
        return [
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Megger calibration information missing - manual review required",
                field_name="megger_calibration",
                found_value=None,
                expected_value=None,
                location=None,
            )
        ]
    return validate_calibration(megger.calibration, test_date, rule_id)
