"""Tests for megger voltage and insulation resistance validators.

Tests MEGGER-02 (test voltage appropriateness) and MEGGER-03 (insulation resistance minimum).
Following TDD: Write tests first, then implement to pass.
"""

import pytest

from src.domain.schemas.evidence import FindingSeverity
from src.domain.schemas.extraction import ExtractedField, MeggerData
from src.domain.validators.megger_voltage import validate_test_voltage
from src.domain.validators.megger_insulation import validate_insulation_resistance


class TestMeggerVoltageValidator:
    """Test MEGGER-02 test voltage appropriateness validation."""

    def test_voltage_appropriate_250v_equipment_500v_test(self):
        """250V equipment with 500V test voltage should return INFO (appropriate)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="250"),
            test_voltage=ExtractedField(name="test_voltage", value="500"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert findings[0].rule_id == "MEGGER-02"

    def test_voltage_too_high_250v_equipment_1000v_test(self):
        """250V equipment with 1000V test should return ERROR (too high, could damage)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="250"),
            test_voltage=ExtractedField(name="test_voltage", value="1000"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert "too high" in findings[0].message.lower() or "exceeds" in findings[0].message.lower()

    def test_voltage_too_low_500v_equipment_500v_test(self):
        """500V equipment with 500V test should return WARNING (too low, might miss issues)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            test_voltage=ExtractedField(name="test_voltage", value="500"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "too low" in findings[0].message.lower() or "below" in findings[0].message.lower()

    def test_voltage_appropriate_500v_equipment_1000v_test(self):
        """500V equipment with 1000V test should return INFO (appropriate)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            test_voltage=ExtractedField(name="test_voltage", value="1000"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_voltage_appropriate_1000v_equipment_1000v_test(self):
        """1000V equipment with 1000V test should return INFO (appropriate)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="1000"),
            test_voltage=ExtractedField(name="test_voltage", value="1000"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_voltage_too_high_500v_equipment_2500v_test(self):
        """500V equipment with 2500V test should return ERROR (too high)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            test_voltage=ExtractedField(name="test_voltage", value="2500"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR

    def test_voltage_missing_equipment_rating(self):
        """Missing equipment rating should return WARNING (can't validate)."""
        megger = MeggerData(
            equipment_voltage_rating=None,
            test_voltage=ExtractedField(name="test_voltage", value="1000"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "missing" in findings[0].message.lower() or "rating" in findings[0].message.lower()

    def test_voltage_missing_test_voltage(self):
        """Missing test voltage should return WARNING."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            test_voltage=None,
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_voltage_unparseable_equipment_rating(self):
        """Unparseable equipment rating should return WARNING."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="invalid"),
            test_voltage=ExtractedField(name="test_voltage", value="1000"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_voltage_unparseable_test_voltage(self):
        """Unparseable test voltage should return WARNING."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            test_voltage=ExtractedField(name="test_voltage", value="N/A"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_voltage_rule_id_correct(self):
        """Rule ID should be MEGGER-02."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="250"),
            test_voltage=ExtractedField(name="test_voltage", value="500"),
        )
        findings = validate_test_voltage(megger)
        assert findings[0].rule_id == "MEGGER-02"

    def test_voltage_custom_rule_id(self):
        """Custom rule ID should be respected."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="250"),
            test_voltage=ExtractedField(name="test_voltage", value="500"),
        )
        findings = validate_test_voltage(megger, rule_id="CUSTOM-01")
        assert findings[0].rule_id == "CUSTOM-01"

    def test_voltage_high_voltage_equipment_2500v_test(self):
        """High voltage (>1000V) equipment with 2500V test should return INFO."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="2000"),
            test_voltage=ExtractedField(name="test_voltage", value="2500"),
        )
        findings = validate_test_voltage(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO


class TestMeggerInsulationValidator:
    """Test MEGGER-03 insulation resistance minimum validation."""

    def test_insulation_above_minimum_250v_equipment(self):
        """250V equipment with 0.5 Mohm should return INFO (above minimum 0.25)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="250"),
            insulation_resistance=ExtractedField(name="resistance", value="0.5"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO
        assert findings[0].rule_id == "MEGGER-03"

    def test_insulation_below_minimum_250v_equipment(self):
        """250V equipment with 0.1 Mohm should return WARNING (below minimum 0.25)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="250"),
            insulation_resistance=ExtractedField(name="resistance", value="0.1"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
        assert "below" in findings[0].message.lower() or "minimum" in findings[0].message.lower()

    def test_insulation_at_minimum_250v_equipment(self):
        """250V equipment with exactly 0.25 Mohm should return INFO (at minimum)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="250"),
            insulation_resistance=ExtractedField(name="resistance", value="0.25"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_insulation_above_minimum_500v_equipment(self):
        """500V equipment with 1.0 Mohm should return INFO (above minimum 0.5)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            insulation_resistance=ExtractedField(name="resistance", value="1.0"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_insulation_below_minimum_500v_equipment(self):
        """500V equipment with 0.4 Mohm should return WARNING (below minimum 0.5)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            insulation_resistance=ExtractedField(name="resistance", value="0.4"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_insulation_above_minimum_1000v_equipment(self):
        """1000V equipment with 2.0 Mohm should return INFO (above minimum 1.0)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="1000"),
            insulation_resistance=ExtractedField(name="resistance", value="2.0"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.INFO

    def test_insulation_below_minimum_1000v_equipment(self):
        """1000V equipment with 0.8 Mohm should return WARNING (below minimum 1.0)."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="1000"),
            insulation_resistance=ExtractedField(name="resistance", value="0.8"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_insulation_missing_equipment_rating(self):
        """Missing equipment rating should return WARNING (can't determine minimum)."""
        megger = MeggerData(
            equipment_voltage_rating=None,
            insulation_resistance=ExtractedField(name="resistance", value="1.0"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_insulation_missing_resistance(self):
        """Missing resistance value should return WARNING."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            insulation_resistance=None,
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_insulation_unparseable_resistance(self):
        """Unparseable resistance should return WARNING."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            insulation_resistance=ExtractedField(name="resistance", value="invalid"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_insulation_unparseable_voltage_rating(self):
        """Unparseable voltage rating should return WARNING."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="N/A"),
            insulation_resistance=ExtractedField(name="resistance", value="1.0"),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING

    def test_insulation_rule_id_correct(self):
        """Rule ID should be MEGGER-03."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="250"),
            insulation_resistance=ExtractedField(name="resistance", value="0.5"),
        )
        findings = validate_insulation_resistance(megger)
        assert findings[0].rule_id == "MEGGER-03"

    def test_insulation_custom_rule_id(self):
        """Custom rule ID should be respected."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="250"),
            insulation_resistance=ExtractedField(name="resistance", value="0.5"),
        )
        findings = validate_insulation_resistance(megger, rule_id="CUSTOM-02")
        assert findings[0].rule_id == "CUSTOM-02"

    def test_insulation_none_value_in_field(self):
        """None value in ExtractedField should return WARNING."""
        megger = MeggerData(
            equipment_voltage_rating=ExtractedField(name="voltage_rating", value="500"),
            insulation_resistance=ExtractedField(name="resistance", value=None),
        )
        findings = validate_insulation_resistance(megger)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.WARNING
