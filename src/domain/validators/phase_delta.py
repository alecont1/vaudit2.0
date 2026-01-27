"""Phase delta temperature validation for thermography reports.

Validates temperature differences between electrical phases.
Implements THERMO-02 validation rule.

Thresholds (per technical standards):
- delta > 15C: Critical failure (REJECTED)
- delta > 3C: Requires Energy Marshal review (REVIEW_NEEDED)
- delta <= 3C: Normal operation (APPROVED)

Core principle: Zero false rejections. When uncertain (missing/unparseable value),
use WARNING (REVIEW_NEEDED) instead of ERROR (REJECTED).
"""

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import MeasurementReading

# Threshold constants (in Celsius)
DELTA_WARNING_THRESHOLD = 3.0  # > 3C requires review
DELTA_ERROR_THRESHOLD = 15.0   # > 15C is critical failure


def validate_phase_delta(
    phase_readings: list[MeasurementReading],
    rule_id: str = "THERMO-02",
) -> list[Finding]:
    """Validate phase delta temperatures from thermography readings.

    Calculates the maximum temperature difference between phases and
    evaluates against threshold values.

    Args:
        phase_readings: List of phase temperature measurements.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings based on delta thresholds:
        - ERROR if delta > 15C (critical failure)
        - WARNING if 3C < delta <= 15C (requires review)
        - INFO if delta <= 3C (normal operation)
        - WARNING if values are missing/unparseable
        - INFO if insufficient data (< 2 readings)
    """
    findings: list[Finding] = []

    # Case 1: Insufficient data (need at least 2 phases to calculate delta)
    if len(phase_readings) < 2:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.INFO,
                message="Phase delta check skipped - insufficient data (need at least 2 phase readings)",
                field_name="phase_temperatures",
                found_value=str(len(phase_readings)),
                expected_value=">= 2",
                location=None,
            )
        )
        return findings

    # Case 2: Extract and parse temperature values
    temperatures: list[float] = []
    phase_labels: list[str] = []
    unparseable_phases: list[str] = []

    for reading in phase_readings:
        label = reading.location_label

        # Check for None value
        if reading.value is None or reading.value.value is None:
            unparseable_phases.append(label)
            continue

        # Try to parse the value as float
        raw_value = reading.value.value
        try:
            temp = float(raw_value)
            temperatures.append(temp)
            phase_labels.append(label)
        except (ValueError, TypeError):
            unparseable_phases.append(label)

    # Case 3: Report unparseable values as WARNING
    if unparseable_phases:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Could not parse temperature value(s) for phase(s): {', '.join(unparseable_phases)} - manual review required",
                field_name="phase_temperatures",
                found_value=", ".join(unparseable_phases),
                expected_value="numeric temperature value",
                location=None,
            )
        )

    # Case 4: Check if we have enough valid temperatures after parsing
    if len(temperatures) < 2:
        # If we already reported unparseable, don't add another finding
        if not findings:
            findings.append(
                Finding(
                    rule_id=rule_id,
                    severity=FindingSeverity.INFO,
                    message="Phase delta check skipped - insufficient valid temperature data",
                    field_name="phase_temperatures",
                    found_value=str(len(temperatures)),
                    expected_value=">= 2",
                    location=None,
                )
            )
        return findings

    # Case 5: Calculate delta (max - min)
    max_temp = max(temperatures)
    min_temp = min(temperatures)
    delta = max_temp - min_temp

    # Find which phases have max and min temperatures for traceability
    max_phase = phase_labels[temperatures.index(max_temp)]
    min_phase = phase_labels[temperatures.index(min_temp)]

    # Case 6: Evaluate against thresholds
    if delta > DELTA_ERROR_THRESHOLD:
        # Critical failure - ERROR
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.ERROR,
                message=f"Phase delta {delta:.1f}C exceeds critical threshold of {DELTA_ERROR_THRESHOLD}C ({max_phase}: {max_temp}C, {min_phase}: {min_temp}C)",
                field_name="phase_delta",
                found_value=f"{delta:.1f}C",
                expected_value=f"<= {DELTA_ERROR_THRESHOLD}C",
                location=None,
            )
        )
    elif delta > DELTA_WARNING_THRESHOLD:
        # Requires review - WARNING
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Phase delta {delta:.1f}C exceeds review threshold of {DELTA_WARNING_THRESHOLD}C ({max_phase}: {max_temp}C, {min_phase}: {min_temp}C)",
                field_name="phase_delta",
                found_value=f"{delta:.1f}C",
                expected_value=f"<= {DELTA_WARNING_THRESHOLD}C",
                location=None,
            )
        )
    else:
        # Normal operation - INFO
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.INFO,
                message=f"Phase delta {delta:.1f}C within normal range (<= {DELTA_WARNING_THRESHOLD}C)",
                field_name="phase_delta",
                found_value=f"{delta:.1f}C",
                expected_value=f"<= {DELTA_WARNING_THRESHOLD}C",
                location=None,
            )
        )

    return findings
