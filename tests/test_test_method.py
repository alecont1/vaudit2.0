"""Tests for grounding test method validator.

TDD tests for GROUND-03 validation rule.
Validates that test method is documented and appropriate for context.
"""

import pytest

from src.domain.schemas.evidence import FindingSeverity
from src.domain.schemas.extraction import ExtractedField, GroundingData
from src.domain.validators.test_method import validate_test_method, VALID_TEST_METHODS


class TestTestMethodValidator:
    """Test GROUND-03 test method validation."""

    # --- Valid method + valid context (INFO) ---

    def test_method_fall_of_potential_new_installation(self):
        """Fall-of-potential with new installation should return INFO (standard method)."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="fall-of-potential"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert findings[0].rule_id == "GROUND-03"
        assert "fall-of-potential" in findings[0].message.lower()

    def test_method_fall_of_potential_existing(self):
        """Fall-of-potential with existing installation should return INFO."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="fall-of-potential"),
            installation_type=ExtractedField(name="installation_type", value="existing"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_method_clamp_on_existing(self):
        """Clamp-on with existing installation should return INFO (valid for maintenance)."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="clamp-on"),
            installation_type=ExtractedField(name="installation_type", value="existing"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_method_slope_any_context(self):
        """Slope method should return INFO for any context."""
        # Test with new
        grounding_new = GroundingData(
            test_method=ExtractedField(name="test_method", value="slope"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings_new = validate_test_method(grounding_new)
        assert len(findings_new) == 1
        assert findings_new[0].severity == FindingSeverity.INFO

        # Test with existing
        grounding_existing = GroundingData(
            test_method=ExtractedField(name="test_method", value="slope"),
            installation_type=ExtractedField(name="installation_type", value="existing"),
        )
        findings_existing = validate_test_method(grounding_existing)
        assert len(findings_existing) == 1
        assert findings_existing[0].severity == FindingSeverity.INFO

    def test_method_attached_rod_valid(self):
        """Attached-rod method should return INFO for valid contexts."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="attached-rod"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_method_star_delta_valid(self):
        """Star-delta method should return INFO for valid contexts."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="star-delta"),
            installation_type=ExtractedField(name="installation_type", value="existing"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    # --- Method inappropriate for context (WARNING) ---

    def test_method_clamp_on_new_installation(self):
        """Clamp-on with new installation should return WARNING (inappropriate)."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="clamp-on"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "inappropriate" in findings[0].message.lower() or "not recommended" in findings[0].message.lower()

    # --- Missing method (ERROR) ---

    def test_method_missing(self):
        """None test method should return ERROR (must be documented)."""
        grounding = GroundingData(
            test_method=None,
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert findings[0].rule_id == "GROUND-03"
        assert "must be documented" in findings[0].message.lower() or "not specified" in findings[0].message.lower()

    def test_method_empty_string(self):
        """Empty string test method should return ERROR (must be documented)."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value=""),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR

    def test_method_whitespace_only(self):
        """Whitespace-only test method should return ERROR."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="   "),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR

    def test_method_none_value_in_field(self):
        """ExtractedField with None value should return ERROR."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value=None),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR

    # --- Unrecognized method (WARNING) ---

    def test_method_unrecognized(self):
        """Unrecognized test method should return WARNING (could be valid)."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="unknown-method"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "unrecognized" in findings[0].message.lower() or "unknown" in findings[0].message.lower()

    def test_method_typo(self):
        """Method with typo should return WARNING."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="fall-of-potental"),  # typo
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    # --- Missing context (WARNING) ---

    def test_method_missing_context(self):
        """Valid method with missing context should return WARNING."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="fall-of-potential"),
            installation_type=None,
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "context" in findings[0].message.lower() or "installation type" in findings[0].message.lower()

    def test_method_empty_context(self):
        """Valid method with empty context should return WARNING."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="fall-of-potential"),
            installation_type=ExtractedField(name="installation_type", value=""),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_method_none_context_value(self):
        """Valid method with None context value should return WARNING."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="fall-of-potential"),
            installation_type=ExtractedField(name="installation_type", value=None),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    # --- Method normalization ---

    def test_method_normalization_case_insensitive(self):
        """Method matching should be case-insensitive."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="Fall-Of-Potential"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_method_normalization_uppercase(self):
        """Uppercase method should be normalized and accepted."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="FALL-OF-POTENTIAL"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_method_normalization_spaces(self):
        """Method with spaces instead of hyphens should be accepted."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="Fall of Potential"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_method_normalization_leading_trailing_spaces(self):
        """Method with leading/trailing spaces should be normalized."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="  fall-of-potential  "),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_method_alias_3_point(self):
        """3-point alias for fall-of-potential should be accepted."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="3-point"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_method_alias_three_point(self):
        """Three-point alias for fall-of-potential should be accepted."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="three-point"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_method_alias_clamp(self):
        """Clamp alias for clamp-on should be accepted."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="clamp"),
            installation_type=ExtractedField(name="installation_type", value="existing"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    # --- Rule ID verification ---

    def test_rule_id_correct(self):
        """All findings should have GROUND-03 rule_id."""
        # Test various scenarios
        test_cases = [
            GroundingData(
                test_method=ExtractedField(name="test_method", value="fall-of-potential"),
                installation_type=ExtractedField(name="installation_type", value="new"),
            ),
            GroundingData(
                test_method=None,
                installation_type=ExtractedField(name="installation_type", value="new"),
            ),
            GroundingData(
                test_method=ExtractedField(name="test_method", value="unknown"),
                installation_type=ExtractedField(name="installation_type", value="new"),
            ),
        ]

        for grounding in test_cases:
            findings = validate_test_method(grounding)
            for finding in findings:
                assert finding.rule_id == "GROUND-03"

    def test_custom_rule_id(self):
        """Custom rule_id should be used when provided."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="fall-of-potential"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding, rule_id="CUSTOM-01")
        assert len(findings) == 1
        assert findings[0].rule_id == "CUSTOM-01"

    # --- Field name verification ---

    def test_field_name_is_test_method(self):
        """Finding should have field_name='test_method'."""
        grounding = GroundingData(
            test_method=ExtractedField(name="test_method", value="fall-of-potential"),
            installation_type=ExtractedField(name="installation_type", value="new"),
        )
        findings = validate_test_method(grounding)
        assert len(findings) == 1
        assert findings[0].field_name == "test_method"

    # --- VALID_TEST_METHODS constant ---

    def test_valid_methods_constant_exists(self):
        """VALID_TEST_METHODS constant should exist and contain expected methods."""
        assert VALID_TEST_METHODS is not None
        assert "fall-of-potential" in VALID_TEST_METHODS
        assert "slope" in VALID_TEST_METHODS
        assert "clamp-on" in VALID_TEST_METHODS
        assert "attached-rod" in VALID_TEST_METHODS
        assert "star-delta" in VALID_TEST_METHODS

    def test_valid_methods_has_context_restrictions(self):
        """VALID_TEST_METHODS should have context restrictions defined."""
        for method, info in VALID_TEST_METHODS.items():
            assert "new_ok" in info, f"Method {method} missing 'new_ok' key"
            assert "existing_ok" in info, f"Method {method} missing 'existing_ok' key"
