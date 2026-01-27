"""Integration tests for validation endpoint (VAL-03).

Tests cover the full validation flow:
- APPROVED, REJECTED, REVIEW_NEEDED status paths
- Error cases (document not found, no extraction)
- Evidence in response
- Custom test date parameter
"""

import io
import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.schemas.extraction import (
    BoundingBox,
    CalibrationInfo,
    ExtractionResult,
    ExtractedField,
    FieldLocation,
)
from src.domain.services.auth import hash_password, create_access_token, hash_token
from src.storage.models import Document, User, Session, ValidationResult, ValidationStatus

# Import MINIMAL_PDF from test_documents
from tests.test_documents import MINIMAL_PDF


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
async def cleanup_uploads():
    """Clean up uploaded files after tests."""
    yield
    upload_dir = Path("data/uploads")
    if upload_dir.exists():
        for file in upload_dir.glob("*"):
            if file.is_file():
                file.unlink()


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user for validation operations."""
    # Clean up any existing test user first
    await db_session.execute(delete(Session).where(Session.user_id.in_(
        select(User.id).where(User.email == "validateep@example.com")
    )))
    await db_session.execute(delete(User).where(User.email == "validateep@example.com"))
    await db_session.commit()

    user = User(
        id=uuid4(),
        email="validateep@example.com",
        hashed_password=hash_password("testpass123"),
        is_active=True,
        is_superuser=False,
        failed_login_attempts=0,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_headers(db_session: AsyncSession, test_user: User):
    """Get auth headers with valid token."""
    token, expires_at = create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        is_admin=test_user.is_superuser,
        remember_me=False,
    )
    # Create session record
    session = Session(
        user_id=test_user.id,
        token_hash=hash_token(token),
        expires_at=expires_at,
        is_revoked=False,
    )
    db_session.add(session)
    await db_session.commit()
    return {"Authorization": f"Bearer {token}"}


def create_mock_extraction_result(
    document_id: str,
    expiration_date: str = "2030-01-15",
    serial_1: str = "ABC123",
    serial_2: str | None = None,
    include_second_calibration: bool = False,
) -> ExtractionResult:
    """Create a mock ExtractionResult for testing validation.

    Args:
        document_id: Document ID for the extraction.
        expiration_date: Expiration date string (default future = valid).
        serial_1: First serial number.
        serial_2: Second serial number (if None, uses serial_1 for consistency).
        include_second_calibration: Whether to include a second calibration entry.
    """
    calibrations = [
        CalibrationInfo(
            instrument_type="thermography",
            serial_number=ExtractedField(
                name="instrument_serial_number",
                value=serial_1,
                location=FieldLocation(
                    page=0,
                    bbox=BoundingBox(left=0.1, top=0.2, right=0.3, bottom=0.25),
                    chunk_id="chunk-1",
                ),
            ),
            calibration_date=ExtractedField(
                name="calibration_date",
                value="01/15/2024",
                location=FieldLocation(
                    page=0,
                    bbox=BoundingBox(left=0.1, top=0.3, right=0.25, bottom=0.35),
                ),
            ),
            expiration_date=ExtractedField(
                name="calibration_expiry",
                value=expiration_date,
                location=FieldLocation(
                    page=0,
                    bbox=BoundingBox(left=0.1, top=0.4, right=0.25, bottom=0.45),
                ),
            ),
        )
    ]

    if include_second_calibration:
        second_serial = serial_2 if serial_2 is not None else serial_1
        calibrations.append(
            CalibrationInfo(
                instrument_type="ultrasound",
                serial_number=ExtractedField(
                    name="instrument_serial_number",
                    value=second_serial,
                    location=FieldLocation(
                        page=1,
                        bbox=BoundingBox(left=0.2, top=0.3, right=0.4, bottom=0.35),
                        chunk_id="chunk-2",
                    ),
                ),
                calibration_date=ExtractedField(
                    name="calibration_date",
                    value="02/20/2024",
                    location=FieldLocation(
                        page=1,
                        bbox=BoundingBox(left=0.2, top=0.4, right=0.35, bottom=0.45),
                    ),
                ),
                expiration_date=ExtractedField(
                    name="calibration_expiry",
                    value=expiration_date,
                    location=FieldLocation(
                        page=1,
                        bbox=BoundingBox(left=0.2, top=0.5, right=0.35, bottom=0.55),
                    ),
                ),
            )
        )

    return ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=2 if include_second_calibration else 1,
        calibrations=calibrations,
        processing_time_ms=1000,
        model_version="dpt-2-latest",
    )


async def upload_test_document(client: AsyncClient, auth_headers: dict) -> str:
    """Helper to upload a test document and return its ID."""
    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
    response = await client.post("/documents/upload", files=files, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


async def upload_and_extract_document(
    client: AsyncClient,
    auth_headers: dict,
    extraction_result: ExtractionResult | None = None,
) -> tuple[str, ExtractionResult]:
    """Helper to upload and extract a document.

    Returns the document ID and the extraction result used.
    """
    document_id = await upload_test_document(client, auth_headers)

    if extraction_result is None:
        extraction_result = create_mock_extraction_result(document_id)

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction_result,
    ):
        response = await client.post(f"/documents/{document_id}/extract", headers=auth_headers)
        assert response.status_code == 200

    return document_id, extraction_result


# =============================================================================
# Validation Status Tests
# =============================================================================


@pytest.mark.asyncio
async def test_validate_document_approved(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test validation with valid calibration returns APPROVED status."""
    # Setup: Upload and extract with valid (future) expiration
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_mock_extraction_result(
        document_id,
        expiration_date="2030-12-31",  # Future date = valid
        serial_1="ABC123",
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    # Act: Validate the document
    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    # Assert
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "APPROVED"
    assert len(data["findings"]) >= 1  # Has INFO findings
    assert data["document_id"] == document_id
    assert "checked_at" in data
    assert "validator_version" in data


@pytest.mark.asyncio
async def test_validate_document_rejected_expired(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation with expired calibration returns REJECTED status."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_mock_extraction_result(
        document_id,
        expiration_date="2020-01-15",  # Past date = expired
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    # Validate
    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "REJECTED"

    # Find ERROR finding about expiration
    error_findings = [f for f in data["findings"] if f["severity"] == "ERROR"]
    assert len(error_findings) >= 1
    assert "expired" in error_findings[0]["message"].lower()


@pytest.mark.asyncio
async def test_validate_document_rejected_serial_mismatch(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation with mismatched serials returns REJECTED status."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_mock_extraction_result(
        document_id,
        expiration_date="2030-12-31",  # Valid (future)
        serial_1="ABC123",
        serial_2="XYZ789",  # Different serial!
        include_second_calibration=True,
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    # Validate
    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "REJECTED"

    # Find VAL-02 error finding
    val02_findings = [f for f in data["findings"] if f["rule_id"] == "VAL-02"]
    error_findings = [f for f in val02_findings if f["severity"] == "ERROR"]
    assert len(error_findings) >= 1
    assert "mismatch" in error_findings[0]["message"].lower()


@pytest.mark.asyncio
async def test_validate_document_review_needed(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation with missing expiration returns REVIEW_NEEDED status."""
    document_id = await upload_test_document(client, auth_headers)

    # Create extraction with missing expiration date
    extraction = ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=1,
        calibrations=[
            CalibrationInfo(
                instrument_type="thermography",
                serial_number=ExtractedField(
                    name="serial_number",
                    value="ABC123",
                    location=FieldLocation(
                        page=0,
                        bbox=BoundingBox(left=0.1, top=0.2, right=0.3, bottom=0.25),
                    ),
                ),
                calibration_date=ExtractedField(
                    name="calibration_date",
                    value="2024-01-15",
                    location=None,
                ),
                expiration_date=None,  # Missing!
            )
        ],
        processing_time_ms=1000,
        model_version="test",
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    # Validate
    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "REVIEW_NEEDED"

    # Find WARNING finding
    warning_findings = [f for f in data["findings"] if f["severity"] == "WARNING"]
    assert len(warning_findings) >= 1
    assert "missing" in warning_findings[0]["message"].lower()


# =============================================================================
# Error Cases
# =============================================================================


@pytest.mark.asyncio
async def test_validate_document_not_found(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test validation fails with 404 for non-existent document."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"

    response = await client.post(f"/documents/{fake_uuid}/validate", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_validate_document_no_extraction(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation fails with 404 when no extraction exists."""
    # Upload document but don't extract
    document_id = await upload_test_document(client, auth_headers)

    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 404
    assert "no extraction" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_validate_extraction_failed(
    client: AsyncClient, db_session: AsyncSession, cleanup_uploads, auth_headers
):
    """Test validation fails with 400 when extraction was failed status."""
    document_id = await upload_test_document(client, auth_headers)

    # Simulate failed extraction
    failed_extraction = ExtractionResult(
        document_id=document_id,
        status="failed",
        page_count=0,
        error_message="API error",
        processing_time_ms=500,
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=failed_extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    # Try to validate
    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 400
    assert "failed" in response.json()["detail"].lower()


# =============================================================================
# Storage and Evidence Tests
# =============================================================================


@pytest.mark.asyncio
async def test_validate_stores_result(
    client: AsyncClient, db_session: AsyncSession, cleanup_uploads, auth_headers
):
    """Test validation stores result in database."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_mock_extraction_result(document_id)

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    # Validate
    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)
    assert response.status_code == 200

    # Check database - use limit(1) since there may be multiple records
    result = await db_session.execute(
        select(ValidationResult)
        .where(ValidationResult.document_id == UUID(document_id))
        .order_by(ValidationResult.created_at.desc())
        .limit(1)
    )
    validation = result.scalar_one_or_none()

    assert validation is not None
    assert validation.status in [
        ValidationStatus.APPROVED,
        ValidationStatus.REJECTED,
        ValidationStatus.REVIEW_NEEDED,
    ]
    assert validation.findings_json is not None

    # Parse findings JSON
    findings = json.loads(validation.findings_json)
    assert len(findings) >= 1


@pytest.mark.asyncio
async def test_validate_response_has_evidence(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation response includes evidence (page, field_name)."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_mock_extraction_result(document_id)

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    # Validate
    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Check findings have evidence
    for finding in data["findings"]:
        assert "rule_id" in finding
        assert "field_name" in finding
        assert "severity" in finding
        assert "message" in finding

    # At least one finding should have page info
    findings_with_page = [f for f in data["findings"] if f["page"] is not None]
    assert len(findings_with_page) >= 1
    assert findings_with_page[0]["page"] >= 0


@pytest.mark.asyncio
async def test_validate_with_custom_test_date(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation uses custom test_date query parameter."""
    document_id = await upload_test_document(client, auth_headers)

    # Expiration date: 2024-06-15
    extraction = create_mock_extraction_result(
        document_id,
        expiration_date="2024-06-15",
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    # Test date BEFORE expiration -> APPROVED
    response_before = await client.post(
        f"/documents/{document_id}/validate",
        params={"test_date": "2024-01-01"},
        headers=auth_headers,
    )
    assert response_before.status_code == 200
    assert response_before.json()["status"] == "APPROVED"

    # Test date AFTER expiration -> REJECTED
    response_after = await client.post(
        f"/documents/{document_id}/validate",
        params={"test_date": "2024-12-01"},
        headers=auth_headers,
    )
    assert response_after.status_code == 200
    assert response_after.json()["status"] == "REJECTED"


# =============================================================================
# Additional Edge Cases
# =============================================================================


@pytest.mark.asyncio
async def test_validate_multiple_calibrations_all_valid(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation with multiple valid calibrations returns APPROVED."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_mock_extraction_result(
        document_id,
        expiration_date="2030-12-31",  # Future date = valid
        serial_1="ABC123",
        serial_2="ABC123",  # Same serial
        include_second_calibration=True,
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"

    # Should have multiple INFO findings (one per calibration + serial check)
    info_findings = [f for f in data["findings"] if f["severity"] == "INFO"]
    assert len(info_findings) >= 2


@pytest.mark.asyncio
async def test_validate_response_includes_validator_version(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation response includes validator version for audit."""
    document_id, _ = await upload_and_extract_document(client, auth_headers)

    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "validator_version" in data
    # Version should be a date string like "2026-01-22"
    assert len(data["validator_version"]) > 0


@pytest.mark.asyncio
async def test_validate_creates_new_validation_record(
    client: AsyncClient, db_session: AsyncSession, cleanup_uploads, auth_headers
):
    """Test each validation creates a new ValidationResult record (append-only)."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_mock_extraction_result(document_id)

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    # Validate twice
    await client.post(f"/documents/{document_id}/validate", headers=auth_headers)
    await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    # Check database has multiple records
    result = await db_session.execute(
        select(ValidationResult)
        .where(ValidationResult.document_id == UUID(document_id))
        .order_by(ValidationResult.created_at.desc())
    )
    validations = result.scalars().all()

    # Should have at least 3: 1 from extraction + 2 from validations
    assert len(validations) >= 3


@pytest.mark.asyncio
async def test_validate_unparseable_date_review_needed(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation with unparseable expiration date returns REVIEW_NEEDED."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_mock_extraction_result(
        document_id,
        expiration_date="not-a-date",  # Unparseable
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REVIEW_NEEDED"

    # Should have WARNING finding about unparseable date
    warning_findings = [f for f in data["findings"] if f["severity"] == "WARNING"]
    assert len(warning_findings) >= 1
    assert "could not parse" in warning_findings[0]["message"].lower()
