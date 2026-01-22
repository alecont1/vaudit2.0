"""Tests for document upload endpoint."""

import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import Document

# Minimal valid PDF bytes (PDF 1.4 format)
MINIMAL_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000052 00000 n
0000000101 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
178
%%EOF"""


@pytest.fixture
async def cleanup_uploads():
    """Clean up uploaded files after tests."""
    yield
    # Clean up data/uploads/ directory after test
    upload_dir = Path("data/uploads")
    if upload_dir.exists():
        for file in upload_dir.glob("*"):
            if file.is_file():
                file.unlink()


@pytest.mark.asyncio
async def test_upload_pdf_success(client: AsyncClient, cleanup_uploads):
    """Test successful PDF upload returns 201 with document metadata."""
    # Create PDF file data
    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

    response = await client.post("/documents/upload", files=files)

    if response.status_code != 201:
        print(f"Error response: {response.json()}")

    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert data["filename"] == "test.pdf"
    assert "file_hash" in data
    assert data["file_size_bytes"] == len(MINIMAL_PDF)
    assert data["status"] == "uploaded"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_upload_non_pdf_rejected(client: AsyncClient, cleanup_uploads):
    """Test non-PDF file upload returns 400."""
    # Create a text file instead of PDF
    text_content = b"This is not a PDF file"
    files = {"file": ("test.txt", io.BytesIO(text_content), "text/plain")}

    response = await client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file_rejected(client: AsyncClient, cleanup_uploads):
    """Test empty file upload returns 400."""
    # Create empty file
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}

    response = await client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_creates_database_record(
    client: AsyncClient, db_session: AsyncSession, cleanup_uploads
):
    """Test upload creates Document record in database."""
    from uuid import UUID

    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

    response = await client.post("/documents/upload", files=files)
    assert response.status_code == 201

    document_id_str = response.json()["id"]
    document_id = UUID(document_id_str)  # Convert string to UUID

    # Query database to verify record exists
    result = await db_session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    assert document is not None
    assert document.filename == "test.pdf"
    assert document.status == "uploaded"
    assert document.file_size_bytes == len(MINIMAL_PDF)


@pytest.mark.asyncio
async def test_upload_file_saved_to_disk(client: AsyncClient, cleanup_uploads):
    """Test uploaded file is saved to disk at correct location."""
    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

    response = await client.post("/documents/upload", files=files)
    assert response.status_code == 201

    # Extract filename from response (has UUID prefix)
    file_hash = response.json()["file_hash"]

    # Verify file exists in upload directory
    upload_dir = Path("data/uploads")
    assert upload_dir.exists()

    # Find file by checking hash matches
    uploaded_files = list(upload_dir.glob("*.pdf"))
    assert len(uploaded_files) > 0, "No PDF files found in upload directory"

    # Verify at least one file has matching content
    file_found = False
    for uploaded_file in uploaded_files:
        content = uploaded_file.read_bytes()
        if content == MINIMAL_PDF:
            file_found = True
            break

    assert file_found, "Uploaded file with matching content not found on disk"
