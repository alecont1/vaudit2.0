"""Integration tests for grounding and megger validation through the validation endpoint.

Tests verify the full validation flow for:
- GROUND-01: Grounding calibration validation
- GROUND-02: Grounding resistance validation
- GROUND-03: Test method validation
- MEGGER-01: Megger calibration validation
- MEGGER-02: Test voltage validation
- MEGGER-03: Insulation resistance validation

Tests use the endpoint flow: upload -> extract (mocked) -> validate
"""

import io
import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

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
    GroundingData,
    MeggerData,
    ThermographyData,
    MeasurementReading,
)
from src.domain.services.auth import hash_password, create_access_token, hash_token
from src.storage.models import User, Session

# Import MINIMAL_PDF from test_documents
from tests.test_documents import MINIMAL_PDF


# =============================================================================
# Test Fixtures and Helpers
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
        select(User.id).where(User.email == "validateint@example.com")
    )))
    await db_session.execute(delete(User).where(User.email == "validateint@example.com"))
    await db_session.commit()

    user = User(
        id=uuid4(),
        email="validateint@example.com",
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


async def upload_test_document(client: AsyncClient, auth_headers: dict) -> str:
    """Helper to upload a test document and return its ID."""
    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
    response = await client.post("/documents/upload", files=files, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


def create_grounding_extraction(
    document_id: str,
    calibration_expiry: str = "2030-12-31",
    resistance_value: str = "3.5",
    test_method: str = "fall-of-potential",
    installation_type: str = "existing",
) -> ExtractionResult:
    """Create a mock ExtractionResult with grounding data.

    Args:
        document_id: Document ID for the extraction.
        calibration_expiry: Calibration expiration date (default future = valid).
        resistance_value: Measured resistance in ohms.
        test_method: Test method used (fall-of-potential, clamp-on, etc.).
        installation_type: Installation type ("new" or "existing").
    """
    return ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=1,
        calibrations=[],
        grounding=GroundingData(
            calibration=CalibrationInfo(
                instrument_type="grounding meter",
                expiration_date=ExtractedField(
                    name="calibration_expiry",
                    value=calibration_expiry,
                    location=FieldLocation(
                        page=0,
                        bbox=BoundingBox(left=0.1, top=0.2, right=0.3, bottom=0.25),
                    ),
                ),
            ),
            resistance_value=ExtractedField(
                name="resistance",
                value=resistance_value,
                location=FieldLocation(
                    page=0,
                    bbox=BoundingBox(left=0.1, top=0.3, right=0.3, bottom=0.35),
                ),
            ),
            test_method=ExtractedField(
                name="test_method",
                value=test_method,
                location=FieldLocation(
                    page=0,
                    bbox=BoundingBox(left=0.1, top=0.4, right=0.3, bottom=0.45),
                ),
            ),
            installation_type=ExtractedField(
                name="installation_type",
                value=installation_type,
                location=FieldLocation(
                    page=0,
                    bbox=BoundingBox(left=0.1, top=0.5, right=0.3, bottom=0.55),
                ),
            ),
        ),
        processing_time_ms=1000,
        model_version="test",
    )


def create_megger_extraction(
    document_id: str,
    calibration_expiry: str = "2030-12-31",
    test_voltage: str = "500",
    equipment_voltage: str = "600",
    insulation_resistance: str = "100",
) -> ExtractionResult:
    """Create a mock ExtractionResult with megger data.

    Args:
        document_id: Document ID for the extraction.
        calibration_expiry: Calibration expiration date (default future = valid).
        test_voltage: Test voltage used (e.g., "500" for 500V).
        equipment_voltage: Equipment rated voltage (e.g., "600" for 600V).
        insulation_resistance: Measured insulation resistance in megohms.
    """
    return ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=1,
        calibrations=[],
        megger=MeggerData(
            calibration=CalibrationInfo(
                instrument_type="megger",
                expiration_date=ExtractedField(
                    name="calibration_expiry",
                    value=calibration_expiry,
                    location=FieldLocation(
                        page=0,
                        bbox=BoundingBox(left=0.1, top=0.2, right=0.3, bottom=0.25),
                    ),
                ),
            ),
            test_voltage=ExtractedField(
                name="test_voltage",
                value=test_voltage,
                location=FieldLocation(
                    page=0,
                    bbox=BoundingBox(left=0.1, top=0.3, right=0.3, bottom=0.35),
                ),
            ),
            equipment_voltage_rating=ExtractedField(
                name="equipment_voltage",
                value=equipment_voltage,
                location=FieldLocation(
                    page=0,
                    bbox=BoundingBox(left=0.1, top=0.4, right=0.3, bottom=0.45),
                ),
            ),
            insulation_resistance=ExtractedField(
                name="insulation_resistance",
                value=insulation_resistance,
                location=FieldLocation(
                    page=0,
                    bbox=BoundingBox(left=0.1, top=0.5, right=0.3, bottom=0.55),
                ),
            ),
        ),
        processing_time_ms=1000,
        model_version="test",
    )


def create_combined_extraction(
    document_id: str,
    grounding_data: GroundingData | None = None,
    megger_data: MeggerData | None = None,
    thermography_data: ThermographyData | None = None,
) -> ExtractionResult:
    """Create extraction with multiple test types."""
    return ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=1,
        calibrations=[],
        thermography=thermography_data,
        grounding=grounding_data,
        megger=megger_data,
        processing_time_ms=1000,
        model_version="test",
    )


# =============================================================================
# Grounding Validation Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_validate_grounding_calibration_expired(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test grounding validation rejects expired calibration (GROUND-01)."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_grounding_extraction(
        document_id,
        calibration_expiry="2020-01-15",  # Past date = expired
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

    assert data["status"] == "REJECTED"

    # Find GROUND-01 error finding
    ground_01_findings = [f for f in data["findings"] if f["rule_id"] == "GROUND-01"]
    error_findings = [f for f in ground_01_findings if f["severity"] == "ERROR"]
    assert len(error_findings) >= 1
    assert "expired" in error_findings[0]["message"].lower()


@pytest.mark.asyncio
async def test_validate_grounding_resistance_too_high(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test grounding validation rejects resistance > 10 ohms (GROUND-02)."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_grounding_extraction(
        document_id,
        resistance_value="15.0",  # > 10 ohms = ERROR
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

    assert data["status"] == "REJECTED"

    # Find GROUND-02 error finding
    ground_02_findings = [f for f in data["findings"] if f["rule_id"] == "GROUND-02"]
    error_findings = [f for f in ground_02_findings if f["severity"] == "ERROR"]
    assert len(error_findings) >= 1
    assert "15.0" in error_findings[0]["message"] or "resistance" in error_findings[0]["message"].lower()


@pytest.mark.asyncio
async def test_validate_grounding_method_missing(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test grounding validation rejects missing test method (GROUND-03)."""
    document_id = await upload_test_document(client, auth_headers)

    # Create extraction with no test method
    extraction = ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=1,
        calibrations=[],
        grounding=GroundingData(
            calibration=CalibrationInfo(
                instrument_type="grounding meter",
                expiration_date=ExtractedField(name="exp", value="2030-12-31"),
            ),
            resistance_value=ExtractedField(name="resistance", value="3.5"),
            test_method=None,  # Missing!
        ),
        processing_time_ms=1000,
        model_version="test",
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

    assert data["status"] == "REJECTED"

    # Find GROUND-03 error finding
    ground_03_findings = [f for f in data["findings"] if f["rule_id"] == "GROUND-03"]
    error_findings = [f for f in ground_03_findings if f["severity"] == "ERROR"]
    assert len(error_findings) >= 1
    assert "method" in error_findings[0]["message"].lower()


@pytest.mark.asyncio
async def test_validate_grounding_complete_pass(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test grounding validation approves valid data."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_grounding_extraction(
        document_id,
        calibration_expiry="2030-12-31",  # Future = valid
        resistance_value="3.5",  # < 5 ohms = excellent
        test_method="fall-of-potential",  # Valid IEEE 81 method
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

    # Should have INFO findings for all grounding validators
    ground_findings = [f for f in data["findings"] if f["rule_id"].startswith("GROUND-")]
    info_findings = [f for f in ground_findings if f["severity"] == "INFO"]
    assert len(info_findings) >= 3  # GROUND-01, GROUND-02, GROUND-03


# =============================================================================
# Megger Validation Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_validate_megger_calibration_expired(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test megger validation rejects expired calibration (MEGGER-01)."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_megger_extraction(
        document_id,
        calibration_expiry="2020-01-15",  # Past date = expired
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

    assert data["status"] == "REJECTED"

    # Find MEGGER-01 error finding
    megger_01_findings = [f for f in data["findings"] if f["rule_id"] == "MEGGER-01"]
    error_findings = [f for f in megger_01_findings if f["severity"] == "ERROR"]
    assert len(error_findings) >= 1
    assert "expired" in error_findings[0]["message"].lower()


@pytest.mark.asyncio
async def test_validate_megger_voltage_too_high(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test megger validation rejects voltage higher than appropriate for equipment (MEGGER-02)."""
    document_id = await upload_test_document(client, auth_headers)
    # For 250V equipment, max safe test voltage is 500V per IEEE 43
    extraction = create_megger_extraction(
        document_id,
        test_voltage="1000",  # Too high for 250V equipment (max safe is 500V)
        equipment_voltage="250",
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

    assert data["status"] == "REJECTED"

    # Find MEGGER-02 error finding
    megger_02_findings = [f for f in data["findings"] if f["rule_id"] == "MEGGER-02"]
    error_findings = [f for f in megger_02_findings if f["severity"] == "ERROR"]
    assert len(error_findings) >= 1
    # Message should mention voltage issue
    assert "voltage" in error_findings[0]["message"].lower() or "2500" in error_findings[0]["message"]


@pytest.mark.asyncio
async def test_validate_megger_insulation_low(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test megger validation warns on low insulation resistance (MEGGER-03)."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_megger_extraction(
        document_id,
        equipment_voltage="600",  # For 600V, minimum is 1 megohm per NETA
        insulation_resistance="0.5",  # Below minimum = WARNING
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

    # Low insulation should be WARNING (not ERROR) per zero false rejections
    assert data["status"] == "REVIEW_NEEDED"

    # Find MEGGER-03 warning finding
    megger_03_findings = [f for f in data["findings"] if f["rule_id"] == "MEGGER-03"]
    warning_findings = [f for f in megger_03_findings if f["severity"] == "WARNING"]
    assert len(warning_findings) >= 1


@pytest.mark.asyncio
async def test_validate_megger_complete_pass(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test megger validation approves valid data."""
    document_id = await upload_test_document(client, auth_headers)
    # For 600V equipment (501-1000V class): recommended test voltage is 1000V
    extraction = create_megger_extraction(
        document_id,
        calibration_expiry="2030-12-31",  # Future = valid
        test_voltage="1000",  # Appropriate for 600V equipment (recommended for 501-1000V class)
        equipment_voltage="600",
        insulation_resistance="100",  # Well above minimum
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

    # Should have INFO findings for all megger validators
    megger_findings = [f for f in data["findings"] if f["rule_id"].startswith("MEGGER-")]
    info_findings = [f for f in megger_findings if f["severity"] == "INFO"]
    assert len(info_findings) >= 3  # MEGGER-01, MEGGER-02, MEGGER-03


# =============================================================================
# Combined Validation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_validate_all_test_types(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation runs all validators when document has thermo + grounding + megger."""
    document_id = await upload_test_document(client, auth_headers)

    # Create extraction with all test types
    extraction = ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=3,
        calibrations=[
            CalibrationInfo(
                instrument_type="thermography camera",
                expiration_date=ExtractedField(name="exp", value="2030-12-31"),
            ),
        ],
        thermography=ThermographyData(
            camera_ambient_temp=ExtractedField(name="ambient", value="25.0"),
            datalogger_temp=ExtractedField(name="datalogger", value="25.0"),
            phase_readings=[
                MeasurementReading(
                    location_label="Phase A",
                    value=ExtractedField(name="temp", value="30.0"),
                ),
                MeasurementReading(
                    location_label="Phase B",
                    value=ExtractedField(name="temp", value="31.0"),
                ),
                MeasurementReading(
                    location_label="Phase C",
                    value=ExtractedField(name="temp", value="30.5"),
                ),
            ],
        ),
        grounding=GroundingData(
            calibration=CalibrationInfo(
                instrument_type="grounding meter",
                expiration_date=ExtractedField(name="exp", value="2030-12-31"),
            ),
            resistance_value=ExtractedField(name="resistance", value="3.5"),
            test_method=ExtractedField(name="method", value="fall-of-potential"),
            installation_type=ExtractedField(name="install_type", value="existing"),  # Required for test method validation
        ),
        megger=MeggerData(
            calibration=CalibrationInfo(
                instrument_type="megger",
                expiration_date=ExtractedField(name="exp", value="2030-12-31"),
            ),
            test_voltage=ExtractedField(name="voltage", value="1000"),  # Recommended for 600V equipment
            equipment_voltage_rating=ExtractedField(name="equip_voltage", value="600"),
            insulation_resistance=ExtractedField(name="insulation", value="100"),
        ),
        processing_time_ms=1000,
        model_version="test",
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

    # Verify findings from all validator types present
    rule_ids = [f["rule_id"] for f in data["findings"]]

    # Check thermography validators ran
    assert any(rid.startswith("THERMO-") for rid in rule_ids)

    # Check grounding validators ran
    assert any(rid.startswith("GROUND-") for rid in rule_ids)

    # Check megger validators ran
    assert any(rid.startswith("MEGGER-") for rid in rule_ids)


@pytest.mark.asyncio
async def test_validate_grounding_megger_only(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation works with grounding and megger but no thermography."""
    document_id = await upload_test_document(client, auth_headers)

    # Create extraction with grounding + megger only (no thermography)
    extraction = ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=2,
        calibrations=[],
        thermography=None,  # No thermography
        grounding=GroundingData(
            calibration=CalibrationInfo(
                instrument_type="grounding meter",
                expiration_date=ExtractedField(name="exp", value="2030-12-31"),
            ),
            resistance_value=ExtractedField(name="resistance", value="4.5"),
            test_method=ExtractedField(name="method", value="slope"),
            installation_type=ExtractedField(name="install_type", value="existing"),  # Required for test method validation
        ),
        megger=MeggerData(
            calibration=CalibrationInfo(
                instrument_type="megger",
                expiration_date=ExtractedField(name="exp", value="2030-12-31"),
            ),
            test_voltage=ExtractedField(name="voltage", value="1000"),  # Recommended for 1000V equipment
            equipment_voltage_rating=ExtractedField(name="equip_voltage", value="1000"),
            insulation_resistance=ExtractedField(name="insulation", value="50"),
        ),
        processing_time_ms=1000,
        model_version="test",
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

    # Verify grounding and megger validators ran
    rule_ids = [f["rule_id"] for f in data["findings"]]
    assert any(rid.startswith("GROUND-") for rid in rule_ids)
    assert any(rid.startswith("MEGGER-") for rid in rule_ids)

    # Verify no thermography findings (since no thermography data)
    assert not any(rid.startswith("THERMO-") for rid in rule_ids)


@pytest.mark.asyncio
async def test_validate_evidence_tracks_grounding_megger(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation evidence_json tracks grounding and megger validation."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_combined_extraction(
        document_id,
        grounding_data=GroundingData(
            calibration=CalibrationInfo(
                instrument_type="grounding meter",
                expiration_date=ExtractedField(name="exp", value="2030-12-31"),
            ),
            resistance_value=ExtractedField(name="resistance", value="3.0"),
            test_method=ExtractedField(name="method", value="fall-of-potential"),
            installation_type=ExtractedField(name="install_type", value="existing"),  # Required for test method validation
        ),
        megger_data=MeggerData(
            calibration=CalibrationInfo(
                instrument_type="megger",
                expiration_date=ExtractedField(name="exp", value="2030-12-31"),
            ),
            test_voltage=ExtractedField(name="voltage", value="1000"),  # Recommended for 600V equipment
            equipment_voltage_rating=ExtractedField(name="equip_voltage", value="600"),
            insulation_resistance=ExtractedField(name="insulation", value="100"),
        ),
    )

    with patch(
        "src.pipeline.extraction.extract_document",
        new_callable=AsyncMock,
        return_value=extraction,
    ):
        await client.post(f"/documents/{document_id}/extract", headers=auth_headers)

    response = await client.post(f"/documents/{document_id}/validate", headers=auth_headers)

    assert response.status_code == 200
    # The response includes findings - grounding and megger data should be validated
    data = response.json()
    assert data["status"] == "APPROVED"

    # Verify both grounding and megger validators produced findings
    ground_findings = [f for f in data["findings"] if f["rule_id"].startswith("GROUND-")]
    megger_findings = [f for f in data["findings"] if f["rule_id"].startswith("MEGGER-")]

    assert len(ground_findings) >= 3  # GROUND-01, GROUND-02, GROUND-03
    assert len(megger_findings) >= 3  # MEGGER-01, MEGGER-02, MEGGER-03


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.asyncio
async def test_validate_grounding_resistance_warning_threshold(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test grounding resistance between 5-10 ohms returns WARNING."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_grounding_extraction(
        document_id,
        resistance_value="7.5",  # Between 5 and 10 = WARNING
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

    # Find GROUND-02 warning finding
    ground_02_findings = [f for f in data["findings"] if f["rule_id"] == "GROUND-02"]
    warning_findings = [f for f in ground_02_findings if f["severity"] == "WARNING"]
    assert len(warning_findings) >= 1


@pytest.mark.asyncio
async def test_validate_grounding_clamp_on_new_installation(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test clamp-on method on new installation returns WARNING."""
    document_id = await upload_test_document(client, auth_headers)
    extraction = create_grounding_extraction(
        document_id,
        test_method="clamp-on",
        installation_type="new",
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

    # Clamp-on on new installation should be WARNING
    assert data["status"] == "REVIEW_NEEDED"

    # Find GROUND-03 warning finding
    ground_03_findings = [f for f in data["findings"] if f["rule_id"] == "GROUND-03"]
    warning_findings = [f for f in ground_03_findings if f["severity"] == "WARNING"]
    assert len(warning_findings) >= 1


@pytest.mark.asyncio
async def test_validate_no_grounding_no_megger_no_findings(
    client: AsyncClient, cleanup_uploads, auth_headers
):
    """Test validation without grounding/megger produces no grounding/megger findings."""
    document_id = await upload_test_document(client, auth_headers)

    # Create extraction with no grounding or megger data
    extraction = ExtractionResult(
        document_id=document_id,
        status="completed",
        page_count=1,
        calibrations=[
            CalibrationInfo(
                instrument_type="generic",
                expiration_date=ExtractedField(name="exp", value="2030-12-31"),
            ),
        ],
        grounding=None,
        megger=None,
        processing_time_ms=1000,
        model_version="test",
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

    # Should be APPROVED (no errors)
    assert data["status"] == "APPROVED"

    # Verify no grounding or megger findings
    rule_ids = [f["rule_id"] for f in data["findings"]]
    assert not any(rid.startswith("GROUND-") for rid in rule_ids)
    assert not any(rid.startswith("MEGGER-") for rid in rule_ids)
