"""Megger insulation resistance validation.

Validates measured insulation resistance meets minimum requirements.
Implements MEGGER-03 validation rule.

Per IEEE 43:
- Minimum resistance depends on voltage class
- Below minimum could indicate insulation degradation

Core principle: Zero false rejections. Resistance below minimum is WARNING
not ERROR (could be measurement conditions, temperature effects, etc.)
"""

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import MeggerData

# Minimum insulation resistance by voltage class (in Megohms)
# Format: (max_equipment_voltage, min_resistance_mohm)
VOLTAGE_CLASS_MIN_RESISTANCE = [
    (250, 0.25),   # <= 250V: min 0.25 Mohm
    (500, 0.5),    # 251-500V: min 0.5 Mohm
    (1000, 1.0),   # 501-1000V: min 1.0 Mohm
    (float('inf'), 1.0),  # > 1000V: min 1.0 Mohm per 1000V (simplified)
]


def _get_min_resistance(equipment_voltage: float) -> float | None:
    """Get minimum required insulation resistance for given equipment voltage.

    Returns minimum resistance in Megohms or None if not found.
    """
    for max_equip, min_resistance in VOLTAGE_CLASS_MIN_RESISTANCE:
        if equipment_voltage <= max_equip:
            return min_resistance
    return None


def validate_insulation_resistance(
    megger: MeggerData,
    rule_id: str = "MEGGER-03",
) -> list[Finding]:
    """Validate insulation resistance meets minimum requirements.

    Checks that the measured insulation resistance meets the minimum
    requirements per IEEE 43 based on equipment voltage class.

    Args:
        megger: Megger test data containing equipment rating and resistance.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings based on resistance check:
        - WARNING if resistance below minimum (review needed)
        - INFO if resistance at or above minimum (approved)
        - WARNING if values are missing/unparseable
    """
    findings: list[Finding] = []

    # Case 1: Missing equipment voltage rating
    if megger.equipment_voltage_rating is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Equipment voltage rating missing - cannot determine minimum insulation resistance requirement",
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
                message="Equipment voltage rating value is empty - cannot determine minimum resistance",
                field_name="equipment_voltage_rating",
                found_value=None,
                expected_value="equipment voltage rating in volts",
                location=megger.equipment_voltage_rating.location,
            )
        )
        return findings

    # Case 3: Missing insulation resistance
    if megger.insulation_resistance is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Insulation resistance value missing - cannot validate minimum requirement",
                field_name="insulation_resistance",
                found_value=None,
                expected_value="insulation resistance in megohms",
                location=None,
            )
        )
        return findings

    # Case 4: Missing or None value in resistance
    if megger.insulation_resistance.value is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Insulation resistance value is empty - cannot validate minimum requirement",
                field_name="insulation_resistance",
                found_value=None,
                expected_value="insulation resistance in megohms",
                location=megger.insulation_resistance.location,
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

    # Case 6: Parse insulation resistance
    try:
        resistance = float(megger.insulation_resistance.value)
    except (ValueError, TypeError):
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Could not parse insulation resistance '{megger.insulation_resistance.value}' - manual review required",
                field_name="insulation_resistance",
                found_value=megger.insulation_resistance.value,
                expected_value="numeric resistance value in megohms",
                location=megger.insulation_resistance.location,
            )
        )
        return findings

    # Case 7: Get minimum resistance for equipment voltage class
    min_resistance = _get_min_resistance(equipment_voltage)
    if min_resistance is None:
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

    # Case 8: Resistance BELOW minimum - WARNING (not ERROR per zero false rejections)
    if resistance < min_resistance:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Insulation resistance {resistance} Mohm below minimum {min_resistance} Mohm for equipment rated {equipment_voltage}V - review required",
                field_name="insulation_resistance",
                found_value=f"{resistance} Mohm",
                expected_value=f">= {min_resistance} Mohm",
                location=megger.insulation_resistance.location,
            )
        )
        return findings

    # Case 9: Resistance at or above minimum - INFO
    findings.append(
        Finding(
            rule_id=rule_id,
            severity=FindingSeverity.INFO,
            message=f"Insulation resistance {resistance} Mohm meets minimum requirement ({min_resistance} Mohm) for equipment rated {equipment_voltage}V",
            field_name="insulation_resistance",
            found_value=f"{resistance} Mohm",
            expected_value=f">= {min_resistance} Mohm",
            location=megger.insulation_resistance.location,
        )
    )

    return findings
