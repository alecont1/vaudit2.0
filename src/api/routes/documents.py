"""Document upload and management endpoints."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.api.dependencies import get_session
from src.domain.schemas.document import DocumentUploadResponse
from src.domain.schemas.extraction import ExtractionResult
from src.pipeline.file_storage import save_upload
from src.storage.models import Document, ValidationResult, ValidationStatus

router = APIRouter(prefix="/documents", tags=["documents"])

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadResponse:
    """Upload a PDF document for validation.

    Accepts PDF files up to 50MB. Returns document metadata including
    a unique ID for subsequent extraction and validation operations.

    Args:
        file: PDF file from multipart form upload
        session: Database session from dependency injection

    Returns:
        DocumentUploadResponse with document ID, hash, and metadata

    Raises:
        HTTPException 400: Not a PDF file
        HTTPException 413: File exceeds 50MB
        HTTPException 500: File save or database failure
    """
    # Validate content type (browsers set this for PDFs)
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {file.content_type}. Only PDF files are accepted.",
        )

    # Check file size before processing
    # Note: file.size might be None for some clients, so we'll also check after reading
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB.",
        )

    try:
        # Save file and get metadata (validates extension and calculates hash)
        file_path, file_hash, file_size = await save_upload(file)

        # Double-check file size after reading
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB.",
            )

    except HTTPException:
        # Re-raise HTTP exceptions from save_upload (400 for invalid PDF/empty file)
        raise
    except Exception as e:
        # Catch any other file system errors
        raise HTTPException(
            status_code=500, detail=f"Failed to save uploaded file: {str(e)}"
        ) from e

    try:
        # Create document record in database
        # user_id=None for now (authentication comes in Phase 6)
        document = Document(
            user_id=None,  # type: ignore  # Will be required after auth
            filename=file.filename or "unknown.pdf",
            file_path=file_path,
            file_hash=file_hash,
            file_size_bytes=file_size,
            status="uploaded",
        )

        session.add(document)
        await session.commit()
        await session.refresh(document)

        return DocumentUploadResponse.model_validate(document)

    except Exception as e:
        # Database operation failed
        raise HTTPException(
            status_code=500, detail=f"Failed to create document record: {str(e)}"
        ) from e


@router.post("/{document_id}/extract", response_model=ExtractionResult, status_code=200)
async def trigger_extraction(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ExtractionResult:
    """Trigger LandingAI extraction on an uploaded document.

    Extracts structured data (calibration dates, serial numbers, measurements)
    from the PDF with visual grounding showing where each field was found.
    """
    # 1. Get document from database
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status not in ("uploaded", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot extract document with status '{document.status}'",
        )

    # 2. Run extraction
    from src.pipeline.extraction import extract_document

    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # Update status to processing
    document.status = "processing"
    await session.commit()

    try:
        extraction_result = await extract_document(file_path)

        # 3. Store extraction result in ValidationResult
        validation = ValidationResult(
            document_id=document_id,
            status=ValidationStatus.PENDING,  # Extraction done, validation pending
            extraction_result_json=extraction_result.model_dump_json(),
            processing_time_ms=extraction_result.processing_time_ms,
            model_version=extraction_result.model_version,
        )
        session.add(validation)

        # Update document status
        document.status = "completed" if extraction_result.status == "completed" else "failed"
        await session.commit()

        # Update document_id in result for response
        extraction_result.document_id = str(document_id)
        return extraction_result

    except ValueError as e:
        # API key not configured
        document.status = "failed"
        await session.commit()
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        document.status = "failed"
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.get("/{document_id}/extraction", response_model=ExtractionResult, status_code=200)
async def get_extraction(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ExtractionResult:
    """Retrieve extraction results for a document.

    Returns the structured extraction data with page/location references
    for each extracted field.
    """
    # Get latest validation result for document
    result = await session.execute(
        select(ValidationResult)
        .where(ValidationResult.document_id == document_id)
        .order_by(ValidationResult.created_at.desc())
    )
    validation = result.scalar_one_or_none()

    if not validation:
        raise HTTPException(status_code=404, detail="No extraction found for document")

    if not validation.extraction_result_json:
        raise HTTPException(status_code=404, detail="Extraction not completed")

    import json

    extraction_data = json.loads(validation.extraction_result_json)
    extraction_data["document_id"] = str(document_id)
    return ExtractionResult(**extraction_data)
