"""Multi-format date parser for AuditEng V2.

Handles three date formats commonly found in calibration certificates:
- ISO: YYYY-MM-DD (unambiguous)
- DD/MM/YYYY: Brazilian standard (FNEC)
- MM/DD/YY: American format (GENSEP)

For ambiguous dates like "01/02/2024", prefers DD/MM/YYYY (Brazilian standard).
"""

import re
from datetime import date
from enum import Enum


class DateFormat(str, Enum):
    """Supported date formats."""

    ISO = "ISO"  # YYYY-MM-DD
    DD_MM_YYYY = "DD_MM_YYYY"  # DD/MM/YYYY (Brazilian)
    MM_DD_YY = "MM_DD_YY"  # MM/DD/YY (American 2-digit year)


# Regex patterns for format detection
_ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DD_MM_YYYY_PATTERN = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
_MM_DD_YY_PATTERN = re.compile(r"^\d{1,2}/\d{1,2}/\d{2}$")


def detect_format(value: str) -> DateFormat | None:
    """Detect the date format without parsing.

    Args:
        value: Raw date string to analyze.

    Returns:
        Detected DateFormat or None if format is unrecognized.
    """
    if not value:
        return None

    value = value.strip()

    if _ISO_PATTERN.match(value):
        return DateFormat.ISO
    if _DD_MM_YYYY_PATTERN.match(value):
        return DateFormat.DD_MM_YYYY
    if _MM_DD_YY_PATTERN.match(value):
        return DateFormat.MM_DD_YY

    return None


def _parse_iso(value: str) -> date | None:
    """Parse ISO format: YYYY-MM-DD."""
    try:
        parts = value.split("-")
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def _parse_dd_mm_yyyy(value: str) -> date | None:
    """Parse DD/MM/YYYY format (Brazilian standard)."""
    try:
        parts = value.split("/")
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def _parse_mm_dd_yy(value: str) -> date | None:
    """Parse MM/DD/YY format (American 2-digit year).

    2-digit years assumed to be 2000s (00-99 -> 2000-2099).
    """
    try:
        parts = value.split("/")
        month = int(parts[0])
        day = int(parts[1])
        year_2digit = int(parts[2])
        year = 2000 + year_2digit
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def parse_date(value: str | None, hint: DateFormat | None = None) -> date | None:
    """Parse a date string in multiple formats.

    Attempts to parse the given date string, trying the hint format first
    if provided, then ISO, DD/MM/YYYY, and MM/DD/YY in order.

    For ambiguous dates like "01/02/2024", DD/MM/YYYY is preferred
    (Brazilian standard per PROJECT.md).

    Args:
        value: Raw date string to parse. Can include surrounding whitespace.
        hint: Optional format hint to try first.

    Returns:
        Parsed datetime.date object, or None if:
        - Input is None, empty, or whitespace-only
        - Format cannot be detected
        - Date is invalid (e.g., Feb 31)
        - Parse fails for any reason

    Note:
        Does NOT raise exceptions. Returns None for any unparseable input.
        Callers should handle None as "date not available".
    """
    # Handle None/empty input
    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    # If hint provided, try that format first
    if hint is not None:
        result = _try_format(value, hint)
        if result is not None:
            return result

    # Detect format from value pattern
    detected = detect_format(value)
    if detected is not None:
        return _try_format(value, detected)

    return None


def _try_format(value: str, fmt: DateFormat) -> date | None:
    """Attempt to parse value using specific format."""
    if fmt == DateFormat.ISO:
        return _parse_iso(value)
    elif fmt == DateFormat.DD_MM_YYYY:
        return _parse_dd_mm_yyyy(value)
    elif fmt == DateFormat.MM_DD_YY:
        return _parse_mm_dd_yy(value)
    return None
