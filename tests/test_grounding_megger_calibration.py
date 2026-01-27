"""Unit tests for grounding and megger calibration validators (GROUND-01, MEGGER-01).

Tests cover:
- GROUND-01: Grounding meter calibration certificate expiration validation
- MEGGER-01: Megger calibration certificate expiration validation

Both validators delegate to the base validate_calibration function,
so these tests focus on the wrapper behavior and rule_id assignment.
"""

import pytest
from datetime import date

from src.domain.validators import (
    validate_grounding_calibration,
    validate_megger_calibration,
)
from src.domain.schemas.extraction import (
    GroundingData,
    MeggerData,
    CalibrationInfo,
    ExtractedField,
    FieldLocation,
    BoundingBox,
)
from src.domain.schemas.evidence import FindingSeverity


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_location() -> FieldLocation:
    """Create a sample field location for testing."""
    return FieldLocation(
        page=0,
        bbox=BoundingBox(left=0.1, top=0.2, right=0.3, bottom=0.25),
        chunk_id="chunk-1",
    )


def create_calibration_info(
    expiration_value: str | None,
    location: FieldLocation | None = None,
) -> CalibrationInfo:
    """Helper to create CalibrationInfo for testing."""
    expiration_field = None
    if expiration_value is not None or location is not None:
        expiration_field = ExtractedField(
            name="expiration_date",
            value=expiration_value,
            location=location,
        )

    return CalibrationInfo(
        instrument_type="grounding",
        serial_number=ExtractedField(
            name="serial_number",
            value="GND-123",
            location=location,
        ),
        calibration_date=ExtractedField(
            name="calibration_date",
            value="2023-01-15",
            location=location,
        ),
        expiration_date=expiration_field,
    )


# =============================================================================
# Grounding Calibration Tests (GROUND-01)
# =============================================================================


class TestGroundingCalibrationValidation:
    """Tests for grounding meter calibration validation (GROUND-01)."""

    def test_grounding_calibration_valid_returns_info(self, sample_location):
        """Valid grounding meter calibration returns INFO severity."""
        calibration = create_calibration_info("2025-12-31", location=sample_location)
        grounding = GroundingData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_grounding_calibration(grounding, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "valid" in findings[0].message.lower()

    def test_grounding_calibration_expired_returns_error(self, sample_location):
        """Expired grounding meter calibration returns ERROR severity."""
        calibration = create_calibration_info("2023-01-15", location=sample_location)
        grounding = GroundingData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_grounding_calibration(grounding, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert "expired" in findings[0].message.lower()

    def test_grounding_calibration_missing_date_returns_warning(self, sample_location):
        """Missing expiration date in calibration returns WARNING."""
        calibration = CalibrationInfo(
            instrument_type="grounding",
            serial_number=ExtractedField(
                name="serial_number",
                value="GND-123",
                location=sample_location,
            ),
            calibration_date=ExtractedField(
                name="calibration_date",
                value="2023-01-15",
                location=sample_location,
            ),
            expiration_date=None,
        )
        grounding = GroundingData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_grounding_calibration(grounding, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "missing" in findings[0].message.lower()
        assert "manual review" in findings[0].message.lower()

    def test_grounding_calibration_no_calibration_info_returns_warning(self):
        """No calibration object at all returns WARNING."""
        grounding = GroundingData(calibration=None)
        test_date = date(2024, 1, 22)

        findings = validate_grounding_calibration(grounding, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "grounding meter calibration" in findings[0].message.lower()
        assert "missing" in findings[0].message.lower()
        assert "manual review" in findings[0].message.lower()

    def test_grounding_calibration_rule_id(self, sample_location):
        """Findings have GROUND-01 rule_id."""
        calibration = create_calibration_info("2025-12-31", location=sample_location)
        grounding = GroundingData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_grounding_calibration(grounding, test_date)

        assert len(findings) == 1
        assert findings[0].rule_id == "GROUND-01"

    def test_grounding_calibration_custom_rule_id(self, sample_location):
        """Custom rule_id is passed through to findings."""
        calibration = create_calibration_info("2025-12-31", location=sample_location)
        grounding = GroundingData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_grounding_calibration(
            grounding, test_date, rule_id="CUSTOM-01"
        )

        assert len(findings) == 1
        assert findings[0].rule_id == "CUSTOM-01"

    def test_grounding_calibration_unparseable_date_returns_warning(
        self, sample_location
    ):
        """Unparseable expiration date returns WARNING."""
        calibration = create_calibration_info("not-a-date", location=sample_location)
        grounding = GroundingData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_grounding_calibration(grounding, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "could not parse" in findings[0].message.lower()


# =============================================================================
# Megger Calibration Tests (MEGGER-01)
# =============================================================================


class TestMeggerCalibrationValidation:
    """Tests for megger calibration validation (MEGGER-01)."""

    def test_megger_calibration_valid_returns_info(self, sample_location):
        """Valid megger calibration returns INFO severity."""
        calibration = create_calibration_info("2025-12-31", location=sample_location)
        calibration.instrument_type = "megger"
        megger = MeggerData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_megger_calibration(megger, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "valid" in findings[0].message.lower()

    def test_megger_calibration_expired_returns_error(self, sample_location):
        """Expired megger calibration returns ERROR severity."""
        calibration = create_calibration_info("2023-01-15", location=sample_location)
        calibration.instrument_type = "megger"
        megger = MeggerData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_megger_calibration(megger, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert "expired" in findings[0].message.lower()

    def test_megger_calibration_missing_date_returns_warning(self, sample_location):
        """Missing expiration date in calibration returns WARNING."""
        calibration = CalibrationInfo(
            instrument_type="megger",
            serial_number=ExtractedField(
                name="serial_number",
                value="MEG-456",
                location=sample_location,
            ),
            calibration_date=ExtractedField(
                name="calibration_date",
                value="2023-01-15",
                location=sample_location,
            ),
            expiration_date=None,
        )
        megger = MeggerData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_megger_calibration(megger, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "missing" in findings[0].message.lower()
        assert "manual review" in findings[0].message.lower()

    def test_megger_calibration_no_calibration_info_returns_warning(self):
        """No calibration object at all returns WARNING."""
        megger = MeggerData(calibration=None)
        test_date = date(2024, 1, 22)

        findings = validate_megger_calibration(megger, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "megger calibration" in findings[0].message.lower()
        assert "missing" in findings[0].message.lower()
        assert "manual review" in findings[0].message.lower()

    def test_megger_calibration_rule_id(self, sample_location):
        """Findings have MEGGER-01 rule_id."""
        calibration = create_calibration_info("2025-12-31", location=sample_location)
        calibration.instrument_type = "megger"
        megger = MeggerData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_megger_calibration(megger, test_date)

        assert len(findings) == 1
        assert findings[0].rule_id == "MEGGER-01"

    def test_megger_calibration_custom_rule_id(self, sample_location):
        """Custom rule_id is passed through to findings."""
        calibration = create_calibration_info("2025-12-31", location=sample_location)
        calibration.instrument_type = "megger"
        megger = MeggerData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_megger_calibration(megger, test_date, rule_id="CUSTOM-02")

        assert len(findings) == 1
        assert findings[0].rule_id == "CUSTOM-02"

    def test_megger_calibration_unparseable_date_returns_warning(self, sample_location):
        """Unparseable expiration date returns WARNING."""
        calibration = create_calibration_info("invalid-date", location=sample_location)
        calibration.instrument_type = "megger"
        megger = MeggerData(calibration=calibration)
        test_date = date(2024, 1, 22)

        findings = validate_megger_calibration(megger, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "could not parse" in findings[0].message.lower()


# =============================================================================
# Field Name Tests
# =============================================================================


class TestCalibrationFieldNames:
    """Tests for field_name values in findings."""

    def test_grounding_no_calibration_field_name(self):
        """No calibration finding has field_name 'grounding_calibration'."""
        grounding = GroundingData(calibration=None)
        test_date = date(2024, 1, 22)

        findings = validate_grounding_calibration(grounding, test_date)

        assert len(findings) == 1
        assert findings[0].field_name == "grounding_calibration"

    def test_megger_no_calibration_field_name(self):
        """No calibration finding has field_name 'megger_calibration'."""
        megger = MeggerData(calibration=None)
        test_date = date(2024, 1, 22)

        findings = validate_megger_calibration(megger, test_date)

        assert len(findings) == 1
        assert findings[0].field_name == "megger_calibration"
