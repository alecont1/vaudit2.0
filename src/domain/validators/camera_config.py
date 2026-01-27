"""Camera configuration validation for thermography reports.

Validates that camera ambient temperature matches datalogger reading.
Implements THERMO-01 validation rule.

Tolerance: 0.0C (exact match required per PROJECT.md)
"""

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import ThermographyData


def validate_camera_config(
    thermography: ThermographyData | None,
    rule_id: str = "THERMO-01",
) -> list[Finding]:
    """Validate camera ambient temperature matches datalogger.

    Per technical standards, camera ambient temperature setting must exactly
    match the external datalogger reading. Any mismatch indicates improper
    camera configuration.

    Args:
        thermography: Extracted thermography data from document.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings:
        - ERROR if temperatures don't match (mismatch = REJECTED)
        - INFO if temperatures match
        - WARNING if either value is missing (needs human review)
    """
    findings: list[Finding] = []

    # Case 1: No thermography data to validate
    if thermography is None:
        return findings

    # Case 2: Missing camera ambient temperature
    if thermography.camera_ambient_temp is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Missing camera ambient temperature - manual review required",
                field_name="camera_ambient_temp",
                found_value=None,
                expected_value=None,
                location=None,
            )
        )
        return findings

    if thermography.camera_ambient_temp.value is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Missing camera ambient temperature - manual review required",
                field_name="camera_ambient_temp",
                found_value=None,
                expected_value=None,
                location=thermography.camera_ambient_temp.location,
            )
        )
        return findings

    # Case 3: Missing datalogger temperature
    if thermography.datalogger_temp is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Missing datalogger temperature - manual review required",
                field_name="datalogger_temp",
                found_value=None,
                expected_value=None,
                location=None,
            )
        )
        return findings

    if thermography.datalogger_temp.value is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message="Missing datalogger temperature - manual review required",
                field_name="datalogger_temp",
                found_value=None,
                expected_value=None,
                location=thermography.datalogger_temp.location,
            )
        )
        return findings

    # Extract values and locations
    camera_value = thermography.camera_ambient_temp.value
    datalogger_value = thermography.datalogger_temp.value
    camera_location = thermography.camera_ambient_temp.location
    datalogger_location = thermography.datalogger_temp.location

    # Case 4: Parse temperatures as floats
    try:
        camera_temp = float(camera_value)
    except ValueError:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Could not parse camera ambient temperature '{camera_value}' - manual review required",
                field_name="camera_ambient_temp",
                found_value=camera_value,
                expected_value=None,
                location=camera_location,
            )
        )
        return findings

    try:
        datalogger_temp = float(datalogger_value)
    except ValueError:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Could not parse datalogger temperature '{datalogger_value}' - manual review required",
                field_name="datalogger_temp",
                found_value=datalogger_value,
                expected_value=None,
                location=datalogger_location,
            )
        )
        return findings

    # Case 5: Compare temperatures (0.0C tolerance = exact match)
    if camera_temp != datalogger_temp:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.ERROR,
                message=f"Camera ambient temperature ({camera_temp}C) does not match datalogger ({datalogger_temp}C)",
                field_name="camera_ambient_temp",
                found_value=str(camera_temp),
                expected_value=str(datalogger_temp),
                location=camera_location,
            )
        )
    else:
        # Case 6: Temperatures match
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.INFO,
                message=f"Camera configuration valid - ambient temperature matches datalogger ({camera_temp}C)",
                field_name="camera_ambient_temp",
                found_value=str(camera_temp),
                expected_value=None,
                location=camera_location,
            )
        )

    return findings
