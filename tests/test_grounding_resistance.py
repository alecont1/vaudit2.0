"""Tests for grounding resistance validation.

TDD test suite for GROUND-02 validation rule.
Tests grounding resistance against technical standard limits (ABNT NBR 5419 / IEEE 142).
"""

import pytest

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import ExtractedField, GroundingData
from src.domain.validators.grounding_resistance import (
    RESISTANCE_ERROR_THRESHOLD,
    RESISTANCE_WARNING_THRESHOLD,
    validate_grounding_resistance,
)


def make_grounding_data(resistance_value: str | None) -> GroundingData:
    """Create GroundingData with given resistance value."""
    if resistance_value is None:
        return GroundingData(resistance_value=None)
    return GroundingData(
        resistance_value=ExtractedField(name="resistance", value=resistance_value)
    )


class TestGroundingResistanceThresholds:
    """Test grounding resistance threshold validation."""

    def test_resistance_good(self):
        """2.5 ohms should be INFO - within acceptable range."""
        grounding = make_grounding_data("2.5")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "2.5" in findings[0].message
        assert "acceptable" in findings[0].message.lower()

    def test_resistance_borderline(self):
        """7.0 ohms should be WARNING - above 5 ohms threshold."""
        grounding = make_grounding_data("7.0")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "7.0" in findings[0].message
        assert "review" in findings[0].message.lower() or "borderline" in findings[0].message.lower()

    def test_resistance_exceeds_max(self):
        """15.0 ohms should be ERROR - exceeds 10 ohms maximum."""
        grounding = make_grounding_data("15.0")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert "15.0" in findings[0].message
        assert "exceeds" in findings[0].message.lower() or "maximum" in findings[0].message.lower()


class TestGroundingResistanceBoundaries:
    """Test boundary conditions for grounding resistance."""

    def test_resistance_exactly_5(self):
        """5.0 ohms should be INFO - exactly at warning threshold is acceptable."""
        grounding = make_grounding_data("5.0")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert "5.0" in findings[0].message

    def test_resistance_exactly_10(self):
        """10.0 ohms should be WARNING - exactly at error threshold is borderline."""
        grounding = make_grounding_data("10.0")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "10.0" in findings[0].message

    def test_resistance_just_above_5(self):
        """5.1 ohms should be WARNING - just above warning threshold."""
        grounding = make_grounding_data("5.1")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_resistance_just_above_10(self):
        """10.1 ohms should be ERROR - just above error threshold."""
        grounding = make_grounding_data("10.1")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR


class TestGroundingResistanceEdgeCases:
    """Test edge cases for grounding resistance (zero false rejections)."""

    def test_resistance_missing_field(self):
        """None resistance value should be WARNING - manual review required."""
        grounding = make_grounding_data(None)
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "missing" in findings[0].message.lower() or "not found" in findings[0].message.lower()

    def test_resistance_unparseable(self):
        """Non-numeric resistance should be WARNING - manual review required."""
        grounding = make_grounding_data("abc")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "parse" in findings[0].message.lower() or "numeric" in findings[0].message.lower()

    def test_resistance_negative(self):
        """Negative resistance should be WARNING - invalid measurement needs review."""
        grounding = make_grounding_data("-1.0")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "negative" in findings[0].message.lower() or "invalid" in findings[0].message.lower()

    def test_resistance_zero(self):
        """Zero resistance should be INFO - technically perfect grounding."""
        grounding = make_grounding_data("0.0")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_resistance_empty_string(self):
        """Empty string resistance should be WARNING - missing data."""
        grounding = GroundingData(
            resistance_value=ExtractedField(name="resistance", value="")
        )
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING


class TestGroundingResistanceMetadata:
    """Test finding metadata and rule ID."""

    def test_rule_id_correct(self):
        """All findings should have GROUND-02 rule_id."""
        grounding = make_grounding_data("5.0")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].rule_id == "GROUND-02"

    def test_custom_rule_id(self):
        """Custom rule_id should be used when provided."""
        grounding = make_grounding_data("5.0")
        findings = validate_grounding_resistance(grounding, rule_id="CUSTOM-01")

        assert len(findings) == 1
        assert findings[0].rule_id == "CUSTOM-01"

    def test_field_name_is_grounding_resistance(self):
        """Finding field_name should be grounding_resistance."""
        grounding = make_grounding_data("5.0")
        findings = validate_grounding_resistance(grounding)

        assert len(findings) == 1
        assert findings[0].field_name == "grounding_resistance"


class TestGroundingResistanceConstants:
    """Test threshold constants are correctly defined."""

    def test_warning_threshold_is_5(self):
        """Warning threshold should be 5.0 ohms."""
        assert RESISTANCE_WARNING_THRESHOLD == 5.0

    def test_error_threshold_is_10(self):
        """Error threshold should be 10.0 ohms."""
        assert RESISTANCE_ERROR_THRESHOLD == 10.0
