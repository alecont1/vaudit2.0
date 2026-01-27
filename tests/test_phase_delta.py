"""Tests for phase delta temperature validator."""

import pytest

from src.domain.schemas.evidence import FindingSeverity
from src.domain.schemas.extraction import ExtractedField, MeasurementReading
from src.domain.validators.phase_delta import validate_phase_delta


class TestPhaseDeltaValidator:
    """Test THERMO-02 phase delta validation."""

    def test_normal_delta_returns_info(self):
        """Delta <= 3C should return INFO (approved)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="26.0")),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="25.5")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "1.0" in findings[0].message or "1.00" in findings[0].message

    def test_warning_delta_returns_warning(self):
        """Delta > 3C but <= 15C should return WARNING (review needed)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="29.0")),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="26.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert findings[0].rule_id == "THERMO-02"

    def test_critical_delta_returns_error(self):
        """Delta > 15C should return ERROR (rejected)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="41.0")),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="26.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR

    def test_exactly_3c_is_acceptable(self):
        """Delta exactly 3.0C should return INFO (boundary condition)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="28.0")),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="26.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_exactly_15c_is_warning(self):
        """Delta exactly 15.0C should return WARNING (boundary condition)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="40.0")),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="26.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_empty_readings_skipped(self):
        """Empty readings list should return INFO (skipped)."""
        findings = validate_phase_delta([])
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "skipped" in findings[0].message.lower() or "insufficient" in findings[0].message.lower()

    def test_single_reading_skipped(self):
        """Single reading should return INFO (skipped, need 2+ for delta)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_unparseable_value_returns_warning(self):
        """Unparseable temperature should return WARNING for human review."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="invalid")),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="26.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) >= 1
        assert any(f.severity == FindingSeverity.WARNING for f in findings)

    def test_none_value_returns_warning(self):
        """None value in reading should return WARNING for human review."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value=None)),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="26.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) >= 1
        assert any(f.severity == FindingSeverity.WARNING for f in findings)
