"""LandingAI ADE extraction service for PDF documents."""

import logging
import os
import time
from pathlib import Path
from typing import Any

from landingai_ade import LandingAIADE
from pydantic import BaseModel, Field

from src.domain.schemas.extraction import (
    BoundingBox,
    CalibrationInfo,
    ExtractionResult,
    ExtractedField,
    FieldLocation,
    MeasurementReading,
)

logger = logging.getLogger(__name__)


# Extraction schema for commissioning reports
class CommissioningReportSchema(BaseModel):
    """Schema for extracting commissioning report data."""

    # Calibration certificate fields
    instrument_serial_number: str | None = Field(
        default=None, description="Serial number of the test instrument"
    )
    calibration_date: str | None = Field(
        default=None, description="Date when instrument was calibrated (any format)"
    )
    calibration_expiry: str | None = Field(
        default=None, description="Date when calibration expires (any format)"
    )
    certificate_number: str | None = Field(
        default=None, description="Calibration certificate number"
    )
    calibrating_laboratory: str | None = Field(
        default=None, description="Name of calibration laboratory"
    )

    # Test metadata
    test_date: str | None = Field(
        default=None, description="Date when the test was performed"
    )
    test_type: str | None = Field(
        default=None, description="Type of test: thermography, grounding, or megger"
    )

    # Camera config (thermography)
    camera_ambient_temp: str | None = Field(
        default=None, description="Ambient temperature configured in camera"
    )
    datalogger_ambient_temp: str | None = Field(
        default=None, description="Ambient temperature from datalogger"
    )


def get_client() -> LandingAIADE:
    """Get LandingAI ADE client."""
    api_key = os.environ.get("VISION_AGENT_API_KEY")
    if not api_key:
        raise ValueError("VISION_AGENT_API_KEY environment variable not set")
    return LandingAIADE(apikey=api_key)


def _parse_grounding(grounding: Any, chunk_id: str | None = None) -> FieldLocation | None:
    """Convert LandingAI grounding info to FieldLocation.

    Args:
        grounding: ChunkGrounding object from LandingAI SDK
        chunk_id: The chunk ID to store for reference
    """
    if not grounding:
        return None

    # LandingAI returns Pydantic objects, access attributes directly
    box = grounding.box if hasattr(grounding, 'box') else None
    if not box:
        return None

    return FieldLocation(
        page=grounding.page if hasattr(grounding, 'page') else 0,
        bbox=BoundingBox(
            left=box.left if hasattr(box, 'left') else 0,
            top=box.top if hasattr(box, 'top') else 0,
            right=box.right if hasattr(box, 'right') else 0,
            bottom=box.bottom if hasattr(box, 'bottom') else 0,
        ),
        chunk_id=chunk_id,
    )


def _find_field_location(
    field_name: str,
    extraction_metadata: dict[str, Any],
    chunks: list[Any],
) -> FieldLocation | None:
    """Find location of extracted field using metadata references.

    Args:
        field_name: Name of the field to find location for
        extraction_metadata: Metadata dict from LandingAI extract response
        chunks: List of Chunk objects from LandingAI parse response
    """
    field_meta = extraction_metadata.get(field_name, {})
    references = field_meta.get("references", [])

    if not references:
        return None

    # Find the chunk matching the first reference
    ref_id = references[0]
    for chunk in chunks:
        # LandingAI returns Pydantic Chunk objects, access id attribute directly
        chunk_id = chunk.id if hasattr(chunk, 'id') else None
        if chunk_id == ref_id:
            grounding = chunk.grounding if hasattr(chunk, 'grounding') else None
            return _parse_grounding(grounding, chunk_id)

    return None


async def extract_document(file_path: Path) -> ExtractionResult:
    """Extract structured data from a PDF document using LandingAI ADE.

    Args:
        file_path: Path to the PDF file

    Returns:
        ExtractionResult with extracted fields and their locations
    """
    start_time = time.time()

    try:
        client = get_client()

        # Step 1: Parse the PDF
        logger.info(f"Parsing document: {file_path}")
        parse_response = client.parse(
            document=file_path,
            model="dpt-2-latest",
        )

        # Step 2: Extract structured data using schema
        from landingai_ade.lib import pydantic_to_json_schema

        schema = pydantic_to_json_schema(CommissioningReportSchema)

        extract_response = client.extract(
            schema=schema,
            markdown=parse_response.markdown,
            model="extract-latest",
        )

        # Step 3: Build extraction result with locations
        chunks = parse_response.chunks if hasattr(parse_response, "chunks") else []
        extraction_data = (
            extract_response.extraction if hasattr(extract_response, "extraction") else {}
        )
        extraction_meta = (
            extract_response.extraction_metadata
            if hasattr(extract_response, "extraction_metadata")
            else {}
        )

        # Map extracted fields with their locations
        def make_field(name: str, value: Any) -> ExtractedField | None:
            if value is None:
                return None
            return ExtractedField(
                name=name,
                value=str(value),
                location=_find_field_location(name, extraction_meta, chunks),
            )

        # Build calibration info
        calibration = CalibrationInfo(
            instrument_type=extraction_data.get("test_type"),
            serial_number=make_field(
                "instrument_serial_number", extraction_data.get("instrument_serial_number")
            ),
            calibration_date=make_field("calibration_date", extraction_data.get("calibration_date")),
            expiration_date=make_field("calibration_expiry", extraction_data.get("calibration_expiry")),
            certificate_number=make_field("certificate_number", extraction_data.get("certificate_number")),
            calibrating_lab=make_field(
                "calibrating_laboratory", extraction_data.get("calibrating_laboratory")
            ),
        )

        processing_time = int((time.time() - start_time) * 1000)

        return ExtractionResult(
            document_id=str(file_path),
            status="completed",
            page_count=(
                parse_response.metadata.page_count if hasattr(parse_response, "metadata") else 0
            ),
            calibrations=[calibration] if calibration.serial_number else [],
            measurements=[],  # TODO: Extract measurements in Phase 4/5
            raw_markdown=parse_response.markdown if hasattr(parse_response, "markdown") else None,
            raw_chunks_count=len(chunks),
            processing_time_ms=processing_time,
            model_version="dpt-2-latest",
        )

    except ValueError as e:
        # Missing API key
        raise
    except Exception as e:
        logger.exception(f"Extraction failed for {file_path}")
        return ExtractionResult(
            document_id=str(file_path),
            status="failed",
            page_count=0,
            error_message=str(e),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )
