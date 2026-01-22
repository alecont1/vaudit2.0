"""File storage utilities for handling uploaded PDFs.

Provides functions for saving uploaded files with unique names,
calculating file hashes, and retrieving file paths.
"""

import hashlib
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile

# Upload directory - created on first save
UPLOAD_DIR = Path("data/uploads")


async def save_upload(file: UploadFile) -> tuple[str, str, int]:
    """Save uploaded file to disk and return metadata.

    Args:
        file: FastAPI UploadFile object from multipart form

    Returns:
        Tuple of (file_path, file_hash, file_size):
        - file_path: Absolute path to saved file
        - file_hash: SHA256 hash of file content
        - file_size: File size in bytes

    Raises:
        HTTPException 400: If file is not a PDF or is empty
    """
    # Validate file extension (case-insensitive)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are accepted. Please upload a .pdf file."
        )

    # Read file content
    content = await file.read()

    # Validate file is not empty
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Calculate SHA256 hash for integrity/deduplication
    file_hash = hashlib.sha256(content).hexdigest()

    # Generate unique filename: {uuid}_{original_filename}
    unique_filename = f"{uuid4()}_{file.filename}"
    file_path = UPLOAD_DIR / unique_filename

    # Create upload directory if it doesn't exist
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Write file asynchronously
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Return absolute path, hash, and size
    return str(file_path.absolute()), file_hash, len(content)


def get_upload_path(filename: str) -> Path:
    """Get full path for a filename in the upload directory.

    Args:
        filename: Name of the file (with or without UUID prefix)

    Returns:
        Full Path object to the file in the upload directory
    """
    return UPLOAD_DIR / filename
