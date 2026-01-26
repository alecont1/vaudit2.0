"""Unit tests for date_parser module (VAL-05).

Tests cover the three supported date formats:
- ISO: YYYY-MM-DD
- DD/MM/YYYY: Brazilian standard
- MM/DD/YY: American 2-digit year

Also tests edge cases, format detection, and format hints.
"""

import pytest
from datetime import date

from src.domain.validators.date_parser import parse_date, detect_format, DateFormat


# =============================================================================
# ISO Format Tests (YYYY-MM-DD)
# =============================================================================


class TestParseISOFormat:
    """Tests for ISO date format (YYYY-MM-DD)."""

    def test_parse_iso_standard(self):
        """Standard ISO date parses correctly."""
        result = parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_iso_with_whitespace(self):
        """ISO date with surrounding whitespace is trimmed and parsed."""
        result = parse_date("  2024-01-15  ")
        assert result == date(2024, 1, 15)

    def test_parse_iso_december(self):
        """ISO date at year end parses correctly."""
        result = parse_date("2024-12-31")
        assert result == date(2024, 12, 31)

    def test_parse_iso_january_first(self):
        """ISO date at year start parses correctly."""
        result = parse_date("2024-01-01")
        assert result == date(2024, 1, 1)


# =============================================================================
# DD/MM/YYYY Format Tests (Brazilian Standard)
# =============================================================================


class TestParseDDMMYYYYFormat:
    """Tests for Brazilian date format (DD/MM/YYYY)."""

    def test_parse_ddmmyyyy_standard(self):
        """Standard DD/MM/YYYY date parses correctly."""
        result = parse_date("15/01/2024")
        assert result == date(2024, 1, 15)

    def test_parse_ddmmyyyy_single_digits(self):
        """DD/MM/YYYY with single digit day/month parses correctly."""
        result = parse_date("5/1/2024")
        assert result == date(2024, 1, 5)

    def test_parse_ddmmyyyy_december(self):
        """DD/MM/YYYY for December 31st parses correctly."""
        result = parse_date("31/12/2024")
        assert result == date(2024, 12, 31)

    def test_parse_ddmmyyyy_february_28(self):
        """DD/MM/YYYY for Feb 28 non-leap year parses correctly."""
        result = parse_date("28/02/2023")
        assert result == date(2023, 2, 28)

    def test_parse_ddmmyyyy_leap_year_feb_29(self):
        """DD/MM/YYYY for Feb 29 leap year parses correctly."""
        result = parse_date("29/02/2024")
        assert result == date(2024, 2, 29)


# =============================================================================
# MM/DD/YY Format Tests (GENSEP American)
# =============================================================================


class TestParseMMDDYYFormat:
    """Tests for American 2-digit year format (MM/DD/YY)."""

    def test_parse_mmddyy_standard(self):
        """Standard MM/DD/YY date parses correctly."""
        result = parse_date("01/15/24")
        assert result == date(2024, 1, 15)

    def test_parse_mmddyy_century(self):
        """MM/DD/YY assumes 2000s century (99 -> 2099)."""
        result = parse_date("12/31/99")
        assert result == date(2099, 12, 31)

    def test_parse_mmddyy_year_00(self):
        """MM/DD/YY with year 00 gives 2000."""
        result = parse_date("01/01/00")
        assert result == date(2000, 1, 1)

    def test_parse_mmddyy_single_digits(self):
        """MM/DD/YY with single digit month/day parses correctly."""
        result = parse_date("1/5/24")
        assert result == date(2024, 1, 5)


# =============================================================================
# Edge Cases
# =============================================================================


class TestParseEdgeCases:
    """Tests for edge cases and error handling."""

    def test_parse_empty_string(self):
        """Empty string returns None."""
        result = parse_date("")
        assert result is None

    def test_parse_none_value(self):
        """None input returns None gracefully."""
        result = parse_date(None)
        assert result is None

    def test_parse_whitespace_only(self):
        """Whitespace-only string returns None."""
        result = parse_date("   ")
        assert result is None

    def test_parse_invalid_date_feb_31(self):
        """Invalid date (Feb 31) returns None."""
        result = parse_date("31/02/2024")
        assert result is None

    def test_parse_invalid_date_feb_30(self):
        """Invalid date (Feb 30) returns None."""
        result = parse_date("30/02/2024")
        assert result is None

    def test_parse_malformed_text(self):
        """Malformed text returns None."""
        result = parse_date("not-a-date")
        assert result is None

    def test_parse_partial_iso(self):
        """Incomplete ISO format returns None."""
        result = parse_date("2024-01")
        assert result is None

    def test_parse_invalid_month_13(self):
        """Invalid month (13 in second position for DD/MM/YYYY) returns None."""
        # In DD/MM/YYYY format: day=01, month=13 -> invalid
        result = parse_date("01/13/2024")
        assert result is None

    def test_parse_invalid_day_32(self):
        """Invalid day (32) returns None."""
        result = parse_date("32/01/2024")
        assert result is None

    def test_parse_negative_values(self):
        """Negative values return None."""
        result = parse_date("-01/02/2024")
        assert result is None


# =============================================================================
# Format Detection Tests
# =============================================================================


class TestDetectFormat:
    """Tests for format detection without parsing."""

    def test_detect_iso_format(self):
        """ISO format is detected correctly."""
        result = detect_format("2024-01-15")
        assert result == DateFormat.ISO

    def test_detect_ddmmyyyy_format(self):
        """DD/MM/YYYY format is detected correctly."""
        result = detect_format("15/01/2024")
        assert result == DateFormat.DD_MM_YYYY

    def test_detect_mmddyy_format(self):
        """MM/DD/YY format is detected correctly."""
        result = detect_format("01/15/24")
        assert result == DateFormat.MM_DD_YY

    def test_detect_unknown_format(self):
        """Unrecognized format returns None."""
        result = detect_format("January 15, 2024")
        assert result is None

    def test_detect_empty_string(self):
        """Empty string returns None."""
        result = detect_format("")
        assert result is None

    def test_detect_with_whitespace(self):
        """Whitespace is trimmed before detection."""
        result = detect_format("  2024-01-15  ")
        assert result == DateFormat.ISO


# =============================================================================
# Format Hint Tests
# =============================================================================


class TestParseWithHint:
    """Tests for parsing with format hints."""

    def test_parse_with_hint_ddmmyyyy(self):
        """When hint provided, that format is tried first."""
        # This date is ambiguous: could be Jan 2 or Feb 1
        result = parse_date("01/02/2024", hint=DateFormat.DD_MM_YYYY)
        assert result == date(2024, 2, 1)  # DD/MM/YYYY: day=01, month=02

    def test_parse_with_hint_iso(self):
        """ISO hint works for ISO format."""
        result = parse_date("2024-01-15", hint=DateFormat.ISO)
        assert result == date(2024, 1, 15)

    def test_parse_ambiguous_prefers_brazilian(self):
        """Ambiguous date without hint prefers DD/MM/YYYY (Brazilian standard).

        Per PROJECT.md decision: For ambiguous dates, prefer Brazilian format.
        Date "01/02/2024" is ambiguous (could be Jan 2 or Feb 1).
        Without hint, DD/MM/YYYY (Brazilian) should be detected first for 4-digit years.
        """
        # Pattern 01/02/2024 matches DD/MM/YYYY format (4-digit year)
        result = parse_date("01/02/2024")
        assert result == date(2024, 2, 1)  # Brazilian: Feb 1st

    def test_parse_hint_wrong_format_falls_back(self):
        """If hint doesn't match, parser falls back to detected format.

        Note: Current implementation tries hint first, if it fails
        it falls back to detection. ISO hint on DD/MM/YYYY pattern
        would fail ISO parse, then detect DD_MM_YYYY pattern.
        """
        # Giving ISO hint but value is DD/MM/YYYY format
        result = parse_date("15/01/2024", hint=DateFormat.ISO)
        # ISO parse fails (no - separators), falls back to detection
        assert result == date(2024, 1, 15)


# =============================================================================
# Parametrized Format Tests
# =============================================================================


@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("2024-01-15", date(2024, 1, 15)),
        ("2024-06-30", date(2024, 6, 30)),
        ("2024-12-25", date(2024, 12, 25)),
        ("2000-01-01", date(2000, 1, 1)),
        ("2099-12-31", date(2099, 12, 31)),
    ],
)
def test_iso_format_variations(date_str: str, expected: date):
    """Parametrized test for various ISO format dates."""
    result = parse_date(date_str)
    assert result == expected


@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("15/01/2024", date(2024, 1, 15)),
        ("30/06/2024", date(2024, 6, 30)),
        ("25/12/2024", date(2024, 12, 25)),
        ("1/1/2024", date(2024, 1, 1)),
        ("31/12/2099", date(2099, 12, 31)),
    ],
)
def test_ddmmyyyy_format_variations(date_str: str, expected: date):
    """Parametrized test for various DD/MM/YYYY format dates."""
    result = parse_date(date_str)
    assert result == expected


@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("01/15/24", date(2024, 1, 15)),
        ("06/30/24", date(2024, 6, 30)),
        ("12/25/24", date(2024, 12, 25)),
        ("01/01/00", date(2000, 1, 1)),
        ("12/31/99", date(2099, 12, 31)),
    ],
)
def test_mmddyy_format_variations(date_str: str, expected: date):
    """Parametrized test for various MM/DD/YY format dates."""
    result = parse_date(date_str)
    assert result == expected


@pytest.mark.parametrize(
    "invalid_value",
    [
        "",
        None,
        "   ",
        "invalid",
        "not-a-date",
        "2024",
        "2024-01",
        "01/2024",
        "January 15, 2024",
        "15-01-2024",  # Dash separators for DD-MM-YYYY not supported
    ],
)
def test_invalid_values_return_none(invalid_value):
    """Parametrized test for various invalid inputs returning None."""
    result = parse_date(invalid_value)
    assert result is None
