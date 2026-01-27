"""Grounding test method verification.

Validates that the test method is documented and appropriate for the context.
Implements GROUND-03 validation rule.

Per IEEE 81:
- fall-of-potential: Standard for new installations (3-point method)
- clamp-on: Only for existing systems (no disconnection required)
- slope: Variation of fall-of-potential, valid for all
- attached-rod: For large grounding systems
- star-delta: For mesh grounding systems

Core principle: Zero false rejections. When uncertain (unrecognized method or
missing context), use WARNING (REVIEW_NEEDED) instead of ERROR (REJECTED).
Exception: Missing test method is ERROR since method traceability is required.
"""

from src.domain.schemas.evidence import Finding, FindingSeverity
from src.domain.schemas.extraction import GroundingData

# Valid methods with context restrictions and aliases
# Format: method_key -> {"aliases": [...], "new_ok": bool, "existing_ok": bool}
VALID_TEST_METHODS: dict[str, dict] = {
    "fall-of-potential": {
        "aliases": ["fall of potential", "3-point", "three-point"],
        "new_ok": True,
        "existing_ok": True,
    },
    "slope": {
        "aliases": [],
        "new_ok": True,
        "existing_ok": True,
    },
    "clamp-on": {
        "aliases": ["clamp on", "clamp"],
        "new_ok": False,
        "existing_ok": True,
    },
    "attached-rod": {
        "aliases": ["attached rod"],
        "new_ok": True,
        "existing_ok": True,
    },
    "star-delta": {
        "aliases": ["star delta"],
        "new_ok": True,
        "existing_ok": True,
    },
}


def _normalize_method(method: str) -> str:
    """Normalize method string for matching.

    Converts to lowercase, strips whitespace, replaces spaces with hyphens.

    Args:
        method: Raw method string from extraction.

    Returns:
        Normalized method string.
    """
    return method.lower().strip().replace(" ", "-")


def _find_method_key(normalized_method: str) -> str | None:
    """Find the canonical method key for a normalized method string.

    Checks both primary keys and aliases.

    Args:
        normalized_method: Normalized method string.

    Returns:
        Canonical method key if found, None otherwise.
    """
    # Check if it matches a primary key
    if normalized_method in VALID_TEST_METHODS:
        return normalized_method

    # Check aliases
    for method_key, info in VALID_TEST_METHODS.items():
        # Normalize aliases for comparison
        normalized_aliases = [_normalize_method(alias) for alias in info["aliases"]]
        if normalized_method in normalized_aliases:
            return method_key

    return None


def validate_test_method(
    grounding: GroundingData,
    rule_id: str = "GROUND-03",
) -> list[Finding]:
    """Validate grounding test method is documented and appropriate.

    Validates that:
    1. Test method is specified (not None/empty)
    2. Test method is recognized (known IEEE 81 method)
    3. Test method is appropriate for installation context

    Args:
        grounding: Grounding data with test_method and installation_type fields.
        rule_id: Validation rule identifier for tracing.

    Returns:
        List of findings based on validation:
        - ERROR if method not specified (must be documented)
        - WARNING if method unrecognized (could be valid)
        - WARNING if context missing (can't verify appropriateness)
        - WARNING if method inappropriate for context
        - INFO if method valid and appropriate for context
    """
    findings: list[Finding] = []

    # Case 1: Check if method is specified
    if grounding.test_method is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.ERROR,
                message="Test method not specified - must be documented for audit traceability",
                field_name="test_method",
                found_value=None,
                expected_value="Documented test method (e.g., fall-of-potential, clamp-on)",
                location=None,
            )
        )
        return findings

    # Case 2: Check if method value is empty/None
    raw_method = grounding.test_method.value
    if raw_method is None or raw_method.strip() == "":
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.ERROR,
                message="Test method value is empty - must be documented for audit traceability",
                field_name="test_method",
                found_value=repr(raw_method),
                expected_value="Documented test method (e.g., fall-of-potential, clamp-on)",
                location=grounding.test_method.location,
            )
        )
        return findings

    # Normalize the method for matching
    normalized_method = _normalize_method(raw_method)
    method_key = _find_method_key(normalized_method)

    # Case 3: Check if method is recognized
    if method_key is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Test method '{raw_method}' is unrecognized - manual review required to verify validity",
                field_name="test_method",
                found_value=raw_method,
                expected_value="Recognized method: fall-of-potential, slope, clamp-on, attached-rod, star-delta",
                location=grounding.test_method.location,
            )
        )
        return findings

    # Method is recognized, now check context
    method_info = VALID_TEST_METHODS[method_key]

    # Case 4: Check if installation context is specified
    if grounding.installation_type is None:
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Test method '{method_key}' is valid but installation type context is missing - cannot verify method appropriateness",
                field_name="test_method",
                found_value=method_key,
                expected_value="Installation type context (new or existing)",
                location=grounding.test_method.location,
            )
        )
        return findings

    # Case 5: Check if context value is valid
    raw_context = grounding.installation_type.value
    if raw_context is None or raw_context.strip() == "":
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Test method '{method_key}' is valid but installation type context is empty - cannot verify method appropriateness",
                field_name="test_method",
                found_value=method_key,
                expected_value="Installation type context (new or existing)",
                location=grounding.test_method.location,
            )
        )
        return findings

    # Normalize context
    normalized_context = raw_context.lower().strip()

    # Case 6: Check context appropriateness
    if normalized_context == "new":
        if not method_info["new_ok"]:
            findings.append(
                Finding(
                    rule_id=rule_id,
                    severity=FindingSeverity.WARNING,
                    message=f"Test method '{method_key}' is not recommended for new installations - fall-of-potential method is standard",
                    field_name="test_method",
                    found_value=f"{method_key} (new installation)",
                    expected_value="fall-of-potential or equivalent for new installations",
                    location=grounding.test_method.location,
                )
            )
            return findings
    elif normalized_context == "existing":
        if not method_info["existing_ok"]:
            findings.append(
                Finding(
                    rule_id=rule_id,
                    severity=FindingSeverity.WARNING,
                    message=f"Test method '{method_key}' is not appropriate for existing installations",
                    field_name="test_method",
                    found_value=f"{method_key} (existing installation)",
                    expected_value="Appropriate method for existing installation testing",
                    location=grounding.test_method.location,
                )
            )
            return findings
    else:
        # Unknown context value - can't validate appropriateness
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=FindingSeverity.WARNING,
                message=f"Test method '{method_key}' is valid but installation type '{raw_context}' is unrecognized - cannot verify method appropriateness",
                field_name="test_method",
                found_value=method_key,
                expected_value="Installation type: 'new' or 'existing'",
                location=grounding.test_method.location,
            )
        )
        return findings

    # Case 7: Method is valid and appropriate for context
    findings.append(
        Finding(
            rule_id=rule_id,
            severity=FindingSeverity.INFO,
            message=f"Test method '{method_key}' is appropriate for {normalized_context} installation testing",
            field_name="test_method",
            found_value=method_key,
            expected_value=f"Valid method for {normalized_context} installation",
            location=grounding.test_method.location,
        )
    )
    return findings
