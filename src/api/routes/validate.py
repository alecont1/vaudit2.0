"""Document validation endpoint for AuditEng V2.

Orchestrates validators and returns evidence-based results.
"""

import json
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.api.dependencies import get_session, require_auth
from src.domain.schemas.evidence import compute_status, Finding
from src.domain.schemas.extraction import ExtractionResult
from src.domain.schemas.validation import (
    FindingResponse,
    ValidationResponse,
    finding_to_response,
)
from src.domain.validators.calibration import validate_calibration
from src.domain.validators.camera_config import validate_camera_config
from src.domain.validators.grounding_calibration import validate_grounding_calibration
from src.domain.validators.grounding_resistance import validate_grounding_resistance
from src.domain.validators.megger_calibration import validate_megger_calibration
from src.domain.validators.megger_insulation import validate_insulation_resistance
from src.domain.validators.megger_voltage import validate_test_voltage
from src.domain.validators.phase_delta import validate_phase_delta
from src.domain.validators.serial import collect_serial_numbers, validate_serial_consistency
from src.domain.validators.test_method import validate_test_method
from src.storage.models import Document, User, ValidationResult, ValidationStatus

router = APIRouter()

# Current rules version for audit trail
RULES_VERSION = "2026-01-27"


@router.post("/{document_id}/validate", response_model=ValidationResponse)
async def validate_document(
    document_id: UUID,
    test_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> ValidationResponse:
    """Validate a document that has been extracted.

    Runs all validators (calibration expiration, serial consistency) on
    the extracted data and returns a consolidated validation result with
    all findings and evidence.

    Args:
        document_id: UUID of the document to validate.
        test_date: Date when the test was performed. Defaults to today.
        session: Database session from dependency injection.

    Returns:
        ValidationResponse with status (APPROVED/REJECTED/REVIEW_NEEDED),
        findings list with page/field evidence, and audit metadata.

    Raises:
        HTTPException 404: Document not found or no extraction exists.
        HTTPException 400: Extraction failed or is not completed.
    """
    # 1. Get document from database
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if user owns document or is admin
    if document.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    # 2. Get latest ValidationResult for document (contains extraction)
    # Use limit(1) since there may be multiple records (append-only audit trail)
    result = await session.execute(
        select(ValidationResult)
        .where(ValidationResult.document_id == document_id)
        .order_by(ValidationResult.created_at.desc())
        .limit(1)
    )
    validation_result = result.scalar_one_or_none()

    if not validation_result:
        raise HTTPException(
            status_code=404,
            detail="No extraction found. Please extract the document first using POST /documents/{id}/extract",
        )

    if not validation_result.extraction_result_json:
        raise HTTPException(
            status_code=400,
            detail="Extraction not completed. Cannot validate without extraction data.",
        )

    # 3. Parse extraction result
    try:
        extraction_data = json.loads(validation_result.extraction_result_json)
        extraction = ExtractionResult(**extraction_data)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid extraction data: {str(e)}",
        )

    # Check extraction was successful
    if extraction.status == "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Extraction failed: {extraction.error_message or 'Unknown error'}",
        )

    # 4. Use today's date if test_date not provided
    if test_date is None:
        test_date = date.today()

    # 5. Run validators and collect all findings
    all_findings: list[Finding] = []

    # 5a. Calibration validation (VAL-01)
    for calibration in extraction.calibrations:
        findings = validate_calibration(calibration, test_date)
        all_findings.extend(findings)

    # 5b. Serial number consistency validation (VAL-02)
    serial_numbers = collect_serial_numbers(extraction)
    serial_findings = validate_serial_consistency(serial_numbers)
    all_findings.extend(serial_findings)

    # 5c. Thermography validation (THERMO-01, THERMO-02, THERMO-03)
    if extraction.thermography:
        # THERMO-01: Camera config validation
        camera_findings = validate_camera_config(extraction.thermography)
        all_findings.extend(camera_findings)

        # THERMO-02: Phase delta validation
        if extraction.thermography.phase_readings:
            delta_findings = validate_phase_delta(extraction.thermography.phase_readings)
            all_findings.extend(delta_findings)

    # THERMO-03: Thermography calibration validation
    # Find thermography calibration and validate with THERMO-03 rule_id
    for calibration in extraction.calibrations:
        if calibration.instrument_type and "thermo" in calibration.instrument_type.lower():
            thermo_cal_findings = validate_calibration(calibration, test_date, rule_id="THERMO-03")
            all_findings.extend(thermo_cal_findings)

    # 5d. Grounding validation (GROUND-01, GROUND-02, GROUND-03)
    if extraction.grounding:
        # GROUND-01: Grounding calibration validation
        grounding_cal_findings = validate_grounding_calibration(extraction.grounding, test_date)
        all_findings.extend(grounding_cal_findings)

        # GROUND-02: Grounding resistance validation
        resistance_findings = validate_grounding_resistance(extraction.grounding)
        all_findings.extend(resistance_findings)

        # GROUND-03: Test method validation
        method_findings = validate_test_method(extraction.grounding)
        all_findings.extend(method_findings)

    # 5e. Megger validation (MEGGER-01, MEGGER-02, MEGGER-03)
    if extraction.megger:
        # MEGGER-01: Megger calibration validation
        megger_cal_findings = validate_megger_calibration(extraction.megger, test_date)
        all_findings.extend(megger_cal_findings)

        # MEGGER-02: Test voltage validation
        voltage_findings = validate_test_voltage(extraction.megger)
        all_findings.extend(voltage_findings)

        # MEGGER-03: Insulation resistance validation
        insulation_findings = validate_insulation_resistance(extraction.megger)
        all_findings.extend(insulation_findings)

    # 6. Compute overall status from findings
    computed_status = compute_status(all_findings)

    # 7. Convert findings to API response format
    finding_responses: list[FindingResponse] = [
        finding_to_response(f) for f in all_findings
    ]

    # 8. Update ValidationResult in database (append-only: create new record)
    # Serialize findings for storage
    findings_json = json.dumps([f.model_dump() for f in all_findings])
    evidence_json = json.dumps({
        "document_id": str(document_id),
        "test_date": str(test_date),
        "calibrations_checked": len(extraction.calibrations),
        "serial_numbers_checked": len(serial_numbers),
        "thermography_validated": extraction.thermography is not None,
        "phase_readings_checked": len(extraction.thermography.phase_readings) if extraction.thermography else 0,
        "grounding_validated": extraction.grounding is not None,
        "megger_validated": extraction.megger is not None,
        "findings_count": len(all_findings),
    })

    # Create new validation result with findings
    new_validation = ValidationResult(
        document_id=document_id,
        status=computed_status,
        findings_json=findings_json,
        evidence_json=evidence_json,
        extraction_result_json=validation_result.extraction_result_json,
        rule_version=RULES_VERSION,
        model_version=validation_result.model_version,
    )
    session.add(new_validation)
    await session.commit()
    await session.refresh(new_validation)

    # 9. Return response
    checked_at = datetime.now(timezone.utc)

    return ValidationResponse(
        document_id=document_id,
        status=computed_status,
        findings=finding_responses,
        checked_at=checked_at,
        validator_version=RULES_VERSION,
    )
