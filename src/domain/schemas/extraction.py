"""Extraction-related Pydantic schemas for API."""

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0-1 range).

    Coordinates are normalized to page dimensions:
    - left/right: 0 = left edge, 1 = right edge
    - top/bottom: 0 = top edge, 1 = bottom edge
    """

    left: float = Field(ge=0.0, le=1.0)
    top: float = Field(ge=0.0, le=1.0)
    right: float = Field(ge=0.0, le=1.0)
    bottom: float = Field(ge=0.0, le=1.0)


class FieldLocation(BaseModel):
    """Location where a field was extracted from in the document."""

    page: int = Field(ge=0, description="Zero-indexed page number")
    bbox: BoundingBox
    chunk_id: str | None = None  # Reference to LandingAI chunk


class ExtractedField(BaseModel):
    """A single extracted field with its source location."""

    name: str
    value: str | None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    location: FieldLocation | None = None


class CalibrationInfo(BaseModel):
    """Extracted calibration certificate information."""

    instrument_type: str | None = None  # thermography, grounding, megger
    serial_number: ExtractedField | None = None
    calibration_date: ExtractedField | None = None
    expiration_date: ExtractedField | None = None
    certificate_number: ExtractedField | None = None
    calibrating_lab: ExtractedField | None = None


class MeasurementReading(BaseModel):
    """A single measurement reading from the report."""

    location_label: str  # e.g., "Panel A", "Circuit 1"
    value: ExtractedField
    unit: str | None = None


class ThermographyData(BaseModel):
    """Thermography-specific extracted data."""

    camera_ambient_temp: ExtractedField | None = None  # Camera's ambient temp setting
    datalogger_temp: ExtractedField | None = None  # External datalogger reading
    phase_readings: list[MeasurementReading] = []  # Phase A, B, C temperatures
    energy_marshal_comment: ExtractedField | None = None  # Comment if phase delta > 3C


class ExtractionResult(BaseModel):
    """Complete extraction result for a document."""

    document_id: str
    status: str  # "completed", "partial", "failed"
    page_count: int

    # Structured extracted data
    calibrations: list[CalibrationInfo] = []
    measurements: list[MeasurementReading] = []
    thermography: ThermographyData | None = None

    # Raw extraction for debugging/audit
    raw_markdown: str | None = None
    raw_chunks_count: int = 0

    # Processing metadata
    processing_time_ms: int | None = None
    model_version: str | None = None
    error_message: str | None = None
