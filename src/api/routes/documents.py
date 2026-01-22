"""Document upload and management endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.domain.schemas.document import DocumentUploadResponse
from src.pipeline.file_storage import save_upload
from src.storage.models import Document

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
