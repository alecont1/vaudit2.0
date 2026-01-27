"""Tests for PDF extraction endpoints."""

import io
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
from src.storage.models import Document, User, Session, ValidationResult

# Import MINIMAL_PDF from test_documents
from tests.test_documents import MINIMAL_PDF


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
    """Create a test user for extraction operations."""
    # Clean up any existing test user first
    await db_session.execute(delete(Session).where(Session.user_id.in_(
        select(User.id).where(User.email == "extracttest@example.com")
    )))
    await db_session.execute(delete(User).where(User.email == "extracttest@example.com"))
    await db_session.commit()

    user = User(
        id=uuid4(),
        email="extracttest@example.com",
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


def create_mock_extraction_result(document_id: str) -> ExtractionResult:
    """Create a mock ExtractionResult with location data for testing."""
    return ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=1,
        calibrations=[
            CalibrationInfo(
                instrument_type="thermography",
                serial_number=ExtractedField(
                    name="instrument_serial_number",
                    value="ABC123",
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
                    value="01/15/2025",
                    location=FieldLocation(
                        page=0,
                        bbox=BoundingBox(left=0.1, top=0.4, right=0.25, bottom=0.45),
                    ),
                ),
            )
        ],
        processing_time_ms=1000,
        model_version="dpt-2-latest",
    )


async def upload_test_document(client: AsyncClient, auth_headers: dict) -> str:
    """Helper to upload a test document and return its ID."""
    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
    response = await client.post("/documents/upload", files=files, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_extract_document_success(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test successful document extraction returns ExtractionResult with location data."""
    # Upload a document first
    document_id = await upload_test_document(client, auth_headers)

    # Mock extract_document function
    mock_result = create_mock_extraction_result(document_id)

    with patch("src.pipeline.extraction.extract_document", new_callable=AsyncMock, return_value=mock_result):
        # Trigger extraction
        response = await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

        if response.status_code != 200:
            print(f"Error response: {response.json()}")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["document_id"] == document_id
        assert data["status"] == "completed"
        assert data["page_count"] == 1
        assert len(data["calibrations"]) == 1
        assert data["calibrations"][0]["instrument_type"] == "thermography"
        assert data["calibrations"][0]["serial_number"]["value"] == "ABC123"
        assert data["processing_time_ms"] == 1000
        assert data["model_version"] == "dpt-2-latest"


@pytest.mark.asyncio
async def test_extract_document_includes_location_data(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test extraction result includes visual grounding data (PDF-04 requirement)."""
    document_id = await upload_test_document(client, auth_headers)

    mock_result = create_mock_extraction_result(document_id)

    with patch("src.pipeline.extraction.extract_document", new_callable=AsyncMock, return_value=mock_result):
        response = await client.post(f"/documents/{document_id}/extract", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        serial_number = data["calibrations"][0]["serial_number"]

        # Verify location data is present
        assert serial_number["location"] is not None
        location = serial_number["location"]

        # Verify page number
        assert location["page"] >= 0
        assert location["page"] == 0

        # Verify bbox coordinates are normalized (0-1 range)
        bbox = location["bbox"]
        assert 0 <= bbox["left"] <= 1
        assert 0 <= bbox["top"] <= 1
        assert 0 <= bbox["right"] <= 1
        assert 0 <= bbox["bottom"] <= 1

        # Verify bbox is valid (right > left, bottom > top)
        assert bbox["right"] > bbox["left"]
        assert bbox["bottom"] > bbox["top"]

        # Verify chunk_id present
        assert location["chunk_id"] == "chunk-1"


@pytest.mark.asyncio
async def test_extract_document_not_found(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test extraction fails with 404 for non-existent document."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"

    response = await client.post(f"/documents/{fake_uuid}/extract", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_missing_api_key(
    client: AsyncClient, cleanup_uploads, db_session: AsyncSession, auth_headers
):
    """Test extraction fails with 503 when API key is not configured."""
    document_id = await upload_test_document(client, auth_headers)

    # Mock extract_document to raise ValueError (missing API key)
    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        side_effect=ValueError("VISION_AGENT_API_KEY environment variable not set"),
    ):
        response = await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

        assert response.status_code == 503
        assert "VISION_AGENT_API_KEY" in response.json()["detail"]

    # Verify document status updated to "failed"
    result = await db_session.execute(
        select(Document).where(Document.id == UUID(document_id))
    )
    document = result.scalar_one_or_none()
    assert document is not None
    assert document.status == "failed"


@pytest.mark.asyncio
async def test_extract_file_not_on_disk(
    client: AsyncClient, db_session: AsyncSession, cleanup_uploads, auth_headers, test_user
):
    """Test extraction fails with 404 when file is missing from disk."""
    # Create document record manually with non-existent file path
    document = Document(
        user_id=test_user.id,  # Set user_id for ownership
        filename="missing.pdf",
        file_path="data/uploads/nonexistent-file.pdf",
        file_hash="fakehash123",
        file_size_bytes=1000,
        status="uploaded",
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    response = await client.post(f"/documents/{document.id}/extract", headers=auth_headers)

    assert response.status_code == 404
    assert "not found on disk" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_invalid_status(
    client: AsyncClient, db_session: AsyncSession, cleanup_uploads, auth_headers, test_user
):
    """Test extraction fails with 400 for invalid document status."""
    # Create document with "processing" status
    document = Document(
        user_id=test_user.id,  # Set user_id for ownership
        filename="processing.pdf",
        file_path="data/uploads/test.pdf",
        file_hash="hash123",
        file_size_bytes=1000,
        status="processing",
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    response = await client.post(f"/documents/{document.id}/extract", headers=auth_headers)

    assert response.status_code == 400
    assert "status" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_extraction_success(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test retrieving stored extraction results returns ExtractionResult."""
    document_id = await upload_test_document(client, auth_headers)

    # Mock extraction and trigger it
    mock_result = create_mock_extraction_result(document_id)

    with patch("src.pipeline.extraction.extract_document", new_callable=AsyncMock, return_value=mock_result):
        # Trigger extraction (stores result in ValidationResult)
        extract_response = await client.post(f"/documents/{document_id}/extract", headers=auth_headers)
        assert extract_response.status_code == 200

    # Retrieve stored extraction
    response = await client.get(f"/documents/{document_id}/extraction", headers=auth_headers)

    if response.status_code != 200:
        print(f"Error response: {response.json()}")

    assert response.status_code == 200
    data = response.json()

    # Verify same structure as extraction result
    assert data["document_id"] == document_id
    assert data["status"] == "completed"
    assert len(data["calibrations"]) == 1
    assert data["calibrations"][0]["serial_number"]["value"] == "ABC123"

    # Verify location data preserved
    location = data["calibrations"][0]["serial_number"]["location"]
    assert location is not None
    assert location["page"] == 0
    assert location["bbox"]["left"] == 0.1


@pytest.mark.asyncio
async def test_get_extraction_not_found(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test retrieval fails with 404 when no extraction exists."""
    document_id = await upload_test_document(client, auth_headers)

    # Try to get extraction before triggering it
    response = await client.get(f"/documents/{document_id}/extraction", headers=auth_headers)

    assert response.status_code == 404
    assert "no extraction found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_extraction_no_results(
    client: AsyncClient, db_session: AsyncSession, cleanup_uploads, auth_headers
):
    """Test retrieval fails with 404 when extraction_result_json is None."""
    # Upload document
    document_id = await upload_test_document(client, auth_headers)

    # Create ValidationResult with no extraction_result_json
    from src.storage.models import ValidationStatus

    validation = ValidationResult(
        document_id=UUID(document_id),
        status=ValidationStatus.PENDING,
        extraction_result_json=None,  # No result stored yet
        processing_time_ms=None,
    )
    db_session.add(validation)
    await db_session.commit()

    response = await client.get(f"/documents/{document_id}/extraction", headers=auth_headers)

    assert response.status_code == 404
    assert "not completed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extraction_failure_handling(
    client: AsyncClient, cleanup_uploads, db_session: AsyncSession, auth_headers
):
    """Test extraction handles failure status and error messages."""
    document_id = await upload_test_document(client, auth_headers)

    # Mock extraction failure
    failed_result = ExtractionResult(
        document_id=document_id,
        status="failed",
        page_count=0,
        error_message="LandingAI API returned error: Invalid document format",
        processing_time_ms=500,
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=failed_result,
    ):
        response = await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

        # Extraction endpoint returns the result even on failure
        assert response.status_code == 200
        data = response.json()

        # Verify failure details
        assert data["status"] == "failed"
        assert data["error_message"] is not None
        assert "Invalid document format" in data["error_message"]

    # Verify document status updated to "failed"
    result = await db_session.execute(
        select(Document).where(Document.id == UUID(document_id))
    )
    document = result.scalar_one_or_none()
    assert document is not None
    assert document.status == "failed"
