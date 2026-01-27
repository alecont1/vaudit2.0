"""Integration tests for thermography validation (THERMO-01, THERMO-02, THERMO-03).

Tests the complete validation flow through the API endpoint with thermography data.
"""

from datetime import date

import pytest

from src.domain.schemas.evidence import FindingSeverity
from src.domain.schemas.extraction import (
    CalibrationInfo,
    ExtractedField,
    MeasurementReading,
    ThermographyData,
)
from src.domain.validators import validate_camera_config, validate_phase_delta, validate_calibration


class TestThermoValidatorUnit:
    """Unit tests for thermography validators."""

    def test_thermo_01_camera_mismatch_rejected(self):
        """THERMO-01: Camera ambient != datalogger -> ERROR (REJECTED)."""
        thermo = ThermographyData(
            camera_ambient_temp=ExtractedField(name="ambient", value="25.0"),
            datalogger_temp=ExtractedField(name="datalogger", value="26.0"),
        )
        findings = validate_camera_config(thermo)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert findings[0].rule_id == "THERMO-01"
        assert "25.0" in findings[0].message
        assert "26.0" in findings[0].message

    def test_thermo_01_camera_match_approved(self):
        """THERMO-01: Camera ambient == datalogger -> INFO (APPROVED)."""
        thermo = ThermographyData(
            camera_ambient_temp=ExtractedField(name="ambient", value="25.0"),
            datalogger_temp=ExtractedField(name="datalogger", value="25.0"),
        )
        findings = validate_camera_config(thermo)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert findings[0].rule_id == "THERMO-01"

    def test_thermo_02_delta_over_15_rejected(self):
        """THERMO-02: Phase delta > 15C -> ERROR (REJECTED)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="41.0")),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="26.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert findings[0].rule_id == "THERMO-02"

    def test_thermo_02_delta_over_3_review_needed(self):
        """THERMO-02: Phase delta > 3C but <= 15C -> WARNING (REVIEW_NEEDED)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="29.0")),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="26.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert findings[0].rule_id == "THERMO-02"

    def test_thermo_02_delta_under_3_approved(self):
        """THERMO-02: Phase delta <= 3C -> INFO (APPROVED)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="27.0")),
            MeasurementReading(location_label="Phase C", value=ExtractedField(name="temp", value="26.0")),
        ]
        findings = validate_phase_delta(readings)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_thermo_03_calibration_uses_existing_validator(self):
        """THERMO-03: Thermography calibration uses validate_calibration with THERMO-03 rule_id."""
        calibration = CalibrationInfo(
            instrument_type="thermography",
            expiration_date=ExtractedField(name="exp", value="2025-01-01"),
        )
        # Test with date after expiration (should fail)
        findings = validate_calibration(calibration, date(2026, 1, 22), rule_id="THERMO-03")
        assert len(findings) == 1
        assert findings[0].rule_id == "THERMO-03"
        assert findings[0].severity == FindingSeverity.ERROR

    def test_thermo_03_calibration_valid(self):
        """THERMO-03: Valid thermography calibration -> INFO."""
        calibration = CalibrationInfo(
            instrument_type="thermography",
            expiration_date=ExtractedField(name="exp", value="2027-12-31"),
        )
        findings = validate_calibration(calibration, date(2026, 1, 22), rule_id="THERMO-03")
        assert len(findings) == 1
        assert findings[0].rule_id == "THERMO-03"
        assert findings[0].severity == FindingSeverity.INFO


class TestThermoValidatorEdgeCases:
    """Edge case tests for zero false rejections principle."""

    def test_missing_camera_temp_warning(self):
        """Missing camera ambient temp -> WARNING (not ERROR)."""
        thermo = ThermographyData(
            datalogger_temp=ExtractedField(name="datalogger", value="25.0"),
        )
        findings = validate_camera_config(thermo)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_missing_datalogger_warning(self):
        """Missing datalogger temp -> WARNING (not ERROR)."""
        thermo = ThermographyData(
            camera_ambient_temp=ExtractedField(name="ambient", value="25.0"),
        )
        findings = validate_camera_config(thermo)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_unparseable_phase_temp_warning(self):
        """Unparseable phase temperature -> WARNING (not ERROR)."""
        readings = [
            MeasurementReading(location_label="Phase A", value=ExtractedField(name="temp", value="25.0")),
            MeasurementReading(location_label="Phase B", value=ExtractedField(name="temp", value="not-a-number")),
        ]
        findings = validate_phase_delta(readings)
        assert any(f.severity == FindingSeverity.WARNING for f in findings)

    def test_no_thermography_data_no_findings(self):
        """No thermography data -> no thermography findings."""
        findings = validate_camera_config(None)
        assert len(findings) == 0

    def test_thermo_03_missing_expiration_warning(self):
        """THERMO-03: Missing expiration date -> WARNING (not ERROR)."""
        calibration = CalibrationInfo(
            instrument_type="thermography",
        )
        findings = validate_calibration(calibration, date(2026, 1, 22), rule_id="THERMO-03")
        assert len(findings) == 1
        assert findings[0].rule_id == "THERMO-03"
        assert findings[0].severity == FindingSeverity.WARNING

    def test_camera_temp_null_value_warning(self):
        """Camera temp field exists but value is None -> WARNING."""
        thermo = ThermographyData(
            camera_ambient_temp=ExtractedField(name="ambient", value=None),
            datalogger_temp=ExtractedField(name="datalogger", value="25.0"),
        )
        findings = validate_camera_config(thermo)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_datalogger_temp_null_value_warning(self):
        """Datalogger temp field exists but value is None -> WARNING."""
        thermo = ThermographyData(
            camera_ambient_temp=ExtractedField(name="ambient", value="25.0"),
            datalogger_temp=ExtractedField(name="datalogger", value=None),
        )
        findings = validate_camera_config(thermo)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_unparseable_camera_temp_warning(self):
        """Unparseable camera temp -> WARNING (not ERROR)."""
        thermo = ThermographyData(
            camera_ambient_temp=ExtractedField(name="ambient", value="not-a-number"),
            datalogger_temp=ExtractedField(name="datalogger", value="25.0"),
        )
        findings = validate_camera_config(thermo)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_unparseable_datalogger_temp_warning(self):
        """Unparseable datalogger temp -> WARNING (not ERROR)."""
        thermo = ThermographyData(
            camera_ambient_temp=ExtractedField(name="ambient", value="25.0"),
            datalogger_temp=ExtractedField(name="datalogger", value="xyz"),
        )
        findings = validate_camera_config(thermo)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
