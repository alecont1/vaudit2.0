"""Megger test voltage validation.

Validates test voltage is appropriate for equipment being tested.
Implements MEGGER-02 validation rule.

Per IEEE 43 / IEC 60364-6:
- Too high voltage could damage equipment insulation
- Too low voltage might not reveal insulation defects

Core principle: Zero false rejections. When uncertain (missing/unparseable value),
use WARNING (REVIEW_NEEDED) instead of ERROR (REJECTED).
"""

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import MeggerData

# Test voltage ranges by equipment voltage class
# Format: (max_equipment_voltage, recommended_test_voltage, max_safe_test_voltage)
VOLTAGE_CLASS_TEST_VOLTAGES = [
    (250, 500, 500),      # <= 250V equipment: test at 500V, max 500V
    (500, 1000, 1000),    # 251-500V: test at 1000V, max 1000V
    (1000, 1000, 2500),   # 501-1000V: test at 1000V, max 2500V
    (float('inf'), 2500, 5000),  # > 1000V: test at 2500V+, max 5000V
]


def _get_voltage_class(equipment_voltage: float) -> tuple[float, float, float] | None:
    """Get the voltage class parameters for given equipment voltage.

    Returns tuple of (max_equipment_voltage, recommended_test_voltage, max_safe_test_voltage)
    or None if not found.
    """
    for max_equip, recommended, max_safe in VOLTAGE_CLASS_TEST_VOLTAGES:
        if equipment_voltage <= max_equip:
            return (max_equip, recommended, max_safe)
    return None


def validate_test_voltage(
    megger: MeggerData,
    rule_id: str = "MEGGER-02",
) -> list[Finding]:
    """Validate test voltage appropriateness for equipment rating.

    Checks that the test voltage used is appropriate for the equipment
    being tested - not too high (could damage) or too low (might miss issues).

    Args:
        megger: Megger test data containing equipment rating and test voltage.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings based on voltage appropriateness:
        - ERROR if test voltage too high for equipment (potential damage)
        - WARNING if test voltage too low (might miss issues)
        - INFO if test voltage appropriate
        - WARNING if values are missing/unparseable
    """
    findings: list[Finding] = []

    # Case 1: Missing equipment voltage rating
    if megger.equipment_voltage_rating is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Equipment voltage rating missing - cannot validate test voltage appropriateness",
                field_name="equipment_voltage_rating",
                found_value=None,
                expected_value="equipment voltage rating in volts",
                location=None,
            )
        )
        return findings

    # Case 2: Missing or None value in equipment rating
    if megger.equipment_voltage_rating.value is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Equipment voltage rating value is empty - cannot validate test voltage",
                field_name="equipment_voltage_rating",
                found_value=None,
                expected_value="equipment voltage rating in volts",
                location=megger.equipment_voltage_rating.location,
            )
        )
        return findings

    # Case 3: Missing test voltage
    if megger.test_voltage is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Test voltage missing - cannot validate voltage appropriateness",
                field_name="test_voltage",
                found_value=None,
                expected_value="test voltage in volts",
                location=None,
            )
        )
        return findings

    # Case 4: Missing or None value in test voltage
    if megger.test_voltage.value is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Test voltage value is empty - cannot validate voltage appropriateness",
                field_name="test_voltage",
                found_value=None,
                expected_value="test voltage in volts",
                location=megger.test_voltage.location,
            )
        )
        return findings

    # Case 5: Parse equipment voltage
    try:
        equipment_voltage = float(megger.equipment_voltage_rating.value)
    except (ValueError, TypeError):
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Could not parse equipment voltage rating '{megger.equipment_voltage_rating.value}' - manual review required",
                field_name="equipment_voltage_rating",
                found_value=megger.equipment_voltage_rating.value,
                expected_value="numeric voltage value",
                location=megger.equipment_voltage_rating.location,
            )
        )
        return findings

    # Case 6: Parse test voltage
    try:
        test_voltage = float(megger.test_voltage.value)
    except (ValueError, TypeError):
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Could not parse test voltage '{megger.test_voltage.value}' - manual review required",
                field_name="test_voltage",
                found_value=megger.test_voltage.value,
                expected_value="numeric voltage value",
                location=megger.test_voltage.location,
            )
        )
        return findings

    # Case 7: Get voltage class for equipment
    voltage_class = _get_voltage_class(equipment_voltage)
    if voltage_class is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Unknown voltage class for equipment rated {equipment_voltage}V - manual review required",
                field_name="equipment_voltage_rating",
                found_value=f"{equipment_voltage}V",
                expected_value="standard voltage class",
                location=megger.equipment_voltage_rating.location,
            )
        )
        return findings

    max_equip, recommended_test, max_safe_test = voltage_class

    # Case 8: Test voltage too HIGH - ERROR (could damage equipment)
    if test_voltage > max_safe_test:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.ERROR,
                message=f"Test voltage {test_voltage}V too high for equipment rated {equipment_voltage}V (max safe: {max_safe_test}V) - potential equipment damage",
                field_name="test_voltage",
                found_value=f"{test_voltage}V",
                expected_value=f"<= {max_safe_test}V",
                location=megger.test_voltage.location,
            )
        )
        return findings

    # Case 9: Test voltage too LOW - WARNING (might miss issues)
    if test_voltage < recommended_test:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Test voltage {test_voltage}V below recommended {recommended_test}V for equipment rated {equipment_voltage}V - may not reveal insulation defects",
                field_name="test_voltage",
                found_value=f"{test_voltage}V",
                expected_value=f">= {recommended_test}V",
                location=megger.test_voltage.location,
            )
        )
        return findings

    # Case 10: Test voltage appropriate - INFO
    findings.append(
        Finding(
            rule_id=rule_id,
            severity=FindingSeverity.INFO,
            message=f"Test voltage {test_voltage}V appropriate for equipment rated {equipment_voltage}V",
            field_name="test_voltage",
            found_value=f"{test_voltage}V",
            expected_value=f"{recommended_test}V - {max_safe_test}V",
            location=megger.test_voltage.location,
        )
    )

    return findings
