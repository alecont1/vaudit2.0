"""Unit tests for validation rules (VAL-01, VAL-02, VAL-04).

Tests cover:
- VAL-01: Calibration certificate expiration validation
- VAL-02: Serial number consistency validation
- VAL-04: Evidence fields in findings
"""

import pytest
from datetime import date

from src.domain.validators import (
    validate_calibration,
    validate_serial_consistency,
    collect_serial_numbers,
)
from src.domain.schemas.extraction import (
    CalibrationInfo,
    ExtractedField,
    FieldLocation,
    BoundingBox,
    ExtractionResult,
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


@pytest.fixture
def sample_location_page_2() -> FieldLocation:
    """Create a sample field location on page 2."""
    return FieldLocation(
        page=1,
        bbox=BoundingBox(left=0.5, top=0.6, right=0.7, bottom=0.65),
        chunk_id="chunk-2",
    )


def create_calibration(
    expiration_value: str | None,
    serial_value: str | None = "ABC123",
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

    serial_field = None
    if serial_value is not None:
        serial_field = ExtractedField(
            name="serial_number",
            value=serial_value,
            location=location,
        )

    return CalibrationInfo(
        instrument_type="thermography",
        serial_number=serial_field,
        calibration_date=ExtractedField(
            name="calibration_date",
            value="2023-01-15",
            location=location,
        ),
        expiration_date=expiration_field,
    )


# =============================================================================
# Calibration Validation Tests (VAL-01)
# =============================================================================


class TestCalibrationValidation:
    """Tests for calibration certificate expiration validation (VAL-01)."""

    def test_calibration_expired_returns_error(self, sample_location):
        """Expired calibration returns ERROR severity."""
        # Expiration 2023-01-15, test date 2024-01-22
        calibration = create_calibration("2023-01-15", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert "expired" in findings[0].message.lower()
        assert findings[0].rule_id == "VAL-01"

    def test_calibration_valid_returns_info(self, sample_location):
        """Valid calibration (future expiration) returns INFO severity."""
        # Expiration 2025-12-31, test date 2024-01-22
        calibration = create_calibration("2025-12-31", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "valid" in findings[0].message.lower()

    def test_calibration_missing_returns_warning(self):
        """Missing expiration date returns WARNING (zero false rejections)."""
        # Create calibration with no expiration_date field at all
        calibration = CalibrationInfo(
            instrument_type="thermography",
            serial_number=ExtractedField(
                name="serial_number",
                value="ABC123",
                location=None,
            ),
            calibration_date=ExtractedField(
                name="calibration_date",
                value="2023-01-15",
                location=None,
            ),
            expiration_date=None,  # Missing entirely
        )
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "missing" in findings[0].message.lower()
        assert "manual review" in findings[0].message.lower()

    def test_calibration_unparseable_returns_warning(self, sample_location):
        """Unparseable expiration date returns WARNING."""
        calibration = create_calibration("not-a-date", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "could not parse" in findings[0].message.lower()
        assert "manual review" in findings[0].message.lower()

    def test_calibration_includes_location(self, sample_location):
        """Finding includes location from input field."""
        calibration = create_calibration("2025-12-31", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].location is not None
        assert findings[0].location.page == 0
        assert findings[0].location.bbox.left == 0.1

    def test_calibration_iso_format(self, sample_location):
        """Calibration with ISO date format is parsed correctly."""
        calibration = create_calibration("2025-06-30", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "2025-06-30" in findings[0].message

    def test_calibration_ddmmyyyy_format(self, sample_location):
        """Calibration with DD/MM/YYYY date format is parsed correctly."""
        calibration = create_calibration("30/06/2025", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        # Should parse to June 30, 2025
        assert "2025-06-30" in findings[0].message

    def test_calibration_mmddyy_format(self, sample_location):
        """Calibration with MM/DD/YY date format is parsed correctly."""
        calibration = create_calibration("06/30/25", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        # Should parse to June 30, 2025
        assert "2025-06-30" in findings[0].message

    def test_calibration_expired_same_day(self, sample_location):
        """Calibration expiring on test date is considered valid (not expired)."""
        calibration = create_calibration("2024-01-22", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        # Same day means not yet expired (expiration >= test_date)
        assert findings[0].severity == FindingSeverity.INFO

    def test_calibration_expired_one_day_before(self, sample_location):
        """Calibration expiring one day before test date is expired."""
        calibration = create_calibration("2024-01-21", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert "expired" in findings[0].message.lower()

    def test_calibration_null_value_in_field(self, sample_location):
        """Expiration field exists but value is None returns WARNING."""
        calibration = CalibrationInfo(
            instrument_type="thermography",
            serial_number=ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
            calibration_date=ExtractedField(
                name="calibration_date",
                value="2023-01-15",
                location=sample_location,
            ),
            expiration_date=ExtractedField(
                name="expiration_date",
                value=None,  # Field exists but value is None
                location=sample_location,
            ),
        )
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING


# =============================================================================
# Serial Validation Tests (VAL-02)
# =============================================================================


class TestSerialValidation:
    """Tests for serial number consistency validation (VAL-02)."""

    def test_serial_matching_returns_info(self, sample_location):
        """All matching serial numbers return INFO severity."""
        serials = [
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
        ]

        findings = validate_serial_consistency(serials)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "consistent" in findings[0].message.lower()
        assert findings[0].rule_id == "VAL-02"

    def test_serial_case_insensitive(self, sample_location):
        """Serial comparison is case-insensitive."""
        serials = [
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
            ExtractedField(
                name="serial_number",
                value="abc123",  # lowercase
                location=sample_location,
            ),
        ]

        findings = validate_serial_consistency(serials)

        # Should be consistent (case-insensitive match)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "consistent" in findings[0].message.lower()

    def test_serial_whitespace_normalized(self, sample_location):
        """Serial comparison normalizes whitespace."""
        serials = [
            ExtractedField(
                name="serial_number",
                value=" ABC123 ",  # with spaces
                location=sample_location,
            ),
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
        ]

        findings = validate_serial_consistency(serials)

        # Should be consistent (whitespace normalized)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_serial_mismatch_returns_error(
        self, sample_location, sample_location_page_2
    ):
        """Mismatched serial numbers return ERROR severity."""
        serials = [
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
            ExtractedField(
                name="serial_number",
                value="XYZ789",
                location=sample_location_page_2,
            ),
        ]

        findings = validate_serial_consistency(serials)

        # First finding should be ERROR about mismatch
        error_findings = [f for f in findings if f.severity == FindingSeverity.ERROR]
        assert len(error_findings) >= 1
        assert "mismatch" in error_findings[0].message.lower()

    def test_serial_single_skipped(self, sample_location):
        """Single serial number skips consistency check (insufficient data)."""
        serials = [
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
        ]

        findings = validate_serial_consistency(serials)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "skipped" in findings[0].message.lower()
        assert "insufficient" in findings[0].message.lower()

    def test_serial_empty_skipped(self):
        """Empty serial list skips consistency check."""
        serials: list[ExtractedField] = []

        findings = validate_serial_consistency(serials)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "skipped" in findings[0].message.lower()

    def test_serial_mismatch_includes_all_values(
        self, sample_location, sample_location_page_2
    ):
        """Mismatch finding includes all found serial values."""
        serials = [
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
            ExtractedField(
                name="serial_number",
                value="XYZ789",
                location=sample_location_page_2,
            ),
        ]

        findings = validate_serial_consistency(serials)

        # Error finding should have both values
        error_finding = next(
            f for f in findings if f.severity == FindingSeverity.ERROR
        )
        assert "ABC123" in error_finding.found_value
        assert "XYZ789" in error_finding.found_value

    def test_serial_three_way_match(self, sample_location):
        """Three matching serial numbers all pass."""
        serials = [
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
        ]

        findings = validate_serial_consistency(serials)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "3 locations" in findings[0].message.lower()

    def test_serial_two_same_one_different(
        self, sample_location, sample_location_page_2
    ):
        """Two matching, one different serial triggers ERROR."""
        serials = [
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
            ExtractedField(
                name="serial_number",
                value="ABC123",
                location=sample_location,
            ),
            ExtractedField(
                name="serial_number",
                value="DEF456",
                location=sample_location_page_2,
            ),
        ]

        findings = validate_serial_consistency(serials)

        error_findings = [f for f in findings if f.severity == FindingSeverity.ERROR]
        assert len(error_findings) >= 1


# =============================================================================
# Evidence Tests (VAL-04)
# =============================================================================


class TestFindingEvidence:
    """Tests for evidence fields in findings (VAL-04)."""

    def test_finding_has_all_evidence_fields(self, sample_location):
        """Finding includes all required evidence fields."""
        calibration = create_calibration("2023-01-15", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        finding = findings[0]

        # Verify all evidence fields present
        assert finding.rule_id is not None
        assert finding.rule_id == "VAL-01"
        assert finding.field_name is not None
        assert finding.field_name == "expiration_date"
        assert finding.found_value is not None  # The parsed date
        assert finding.expected_value is not None  # What was expected
        assert finding.location is not None
        assert finding.location.page == 0

    def test_finding_includes_bbox(self, sample_location):
        """Finding location includes bounding box coordinates."""
        calibration = create_calibration("2023-01-15", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        finding = findings[0]

        assert finding.location.bbox is not None
        assert finding.location.bbox.left == 0.1
        assert finding.location.bbox.top == 0.2
        assert finding.location.bbox.right == 0.3
        assert finding.location.bbox.bottom == 0.25

    def test_finding_message_is_descriptive(self, sample_location):
        """Finding message is human-readable and descriptive."""
        calibration = create_calibration("2023-01-15", location=sample_location)
        test_date = date(2024, 1, 22)

        findings = validate_calibration(calibration, test_date)

        assert len(findings) == 1
        finding = findings[0]

        # Message should mention expiration, the date, and test date
        assert "expired" in finding.message.lower()
        assert "2023-01-15" in finding.message
        assert "2024-01-22" in finding.message


# =============================================================================
# collect_serial_numbers Tests
# =============================================================================


class TestCollectSerialNumbers:
    """Tests for collect_serial_numbers helper function."""

    def test_collect_serial_numbers(self, sample_location):
        """Extracts serials from ExtractionResult.calibrations."""
        extraction = ExtractionResult(
            document_id="test-doc-id",
            status="completed",
            page_count=1,
            calibrations=[
                CalibrationInfo(
                    instrument_type="thermography",
                    serial_number=ExtractedField(
                        name="serial_number",
                        value="ABC123",
                        location=sample_location,
                    ),
                    calibration_date=ExtractedField(
                        name="calibration_date",
                        value="2023-01-15",
                        location=sample_location,
                    ),
                    expiration_date=ExtractedField(
                        name="expiration_date",
                        value="2025-01-15",
                        location=sample_location,
                    ),
                ),
                CalibrationInfo(
                    instrument_type="thermography",
                    serial_number=ExtractedField(
                        name="serial_number",
                        value="DEF456",
                        location=sample_location,
                    ),
                    calibration_date=None,
                    expiration_date=None,
                ),
            ],
            processing_time_ms=1000,
            model_version="test",
        )

        serials = collect_serial_numbers(extraction)

        assert len(serials) == 2
        assert serials[0].value == "ABC123"
        assert serials[1].value == "DEF456"

    def test_collect_serial_numbers_empty(self):
        """Returns empty list when no calibrations."""
        extraction = ExtractionResult(
            document_id="test-doc-id",
            status="completed",
            page_count=1,
            calibrations=[],
            processing_time_ms=1000,
            model_version="test",
        )

        serials = collect_serial_numbers(extraction)

        assert len(serials) == 0

    def test_collect_serial_numbers_none_serial(self, sample_location):
        """Skips calibrations with None serial_number."""
        extraction = ExtractionResult(
            document_id="test-doc-id",
            status="completed",
            page_count=1,
            calibrations=[
                CalibrationInfo(
                    instrument_type="thermography",
                    serial_number=None,  # No serial
                    calibration_date=ExtractedField(
                        name="calibration_date",
                        value="2023-01-15",
                        location=sample_location,
                    ),
                    expiration_date=None,
                ),
                CalibrationInfo(
                    instrument_type="thermography",
                    serial_number=ExtractedField(
                        name="serial_number",
                        value="ABC123",
                        location=sample_location,
                    ),
                    calibration_date=None,
                    expiration_date=None,
                ),
            ],
            processing_time_ms=1000,
            model_version="test",
        )

        serials = collect_serial_numbers(extraction)

        assert len(serials) == 1
        assert serials[0].value == "ABC123"
