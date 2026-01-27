"""Tests for document upload endpoint."""

import io
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.services.auth import hash_password, create_access_token, hash_token
from src.storage.models import Document, User, Session

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


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user for document operations."""
    # Clean up any existing test user first
    await db_session.execute(delete(Session).where(Session.user_id.in_(
        select(User.id).where(User.email == "doctest@example.com")
    )))
    await db_session.execute(delete(User).where(User.email == "doctest@example.com"))
    await db_session.commit()

    user = User(
        id=uuid4(),
        email="doctest@example.com",
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


@pytest.mark.asyncio
async def test_upload_pdf_success(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test successful PDF upload returns 201 with document metadata."""
    # Create PDF file data
    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

    response = await client.post("/documents/upload", files=files, headers=auth_headers)

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
async def test_upload_non_pdf_rejected(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test non-PDF file upload returns 400."""
    # Create a text file instead of PDF
    text_content = b"This is not a PDF file"
    files = {"file": ("test.txt", io.BytesIO(text_content), "text/plain")}

    response = await client.post("/documents/upload", files=files, headers=auth_headers)

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file_rejected(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test empty file upload returns 400."""
    # Create empty file
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}

    response = await client.post("/documents/upload", files=files, headers=auth_headers)

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_creates_database_record(
    client: AsyncClient, db_session: AsyncSession, cleanup_uploads, auth_headers, test_user
):
    """Test upload creates Document record in database."""
    from uuid import UUID

    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

    response = await client.post("/documents/upload", files=files, headers=auth_headers)
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
    assert document.user_id == test_user.id  # Verify user_id is set


@pytest.mark.asyncio
async def test_upload_file_saved_to_disk(client: AsyncClient, cleanup_uploads, auth_headers):
    """Test uploaded file is saved to disk at correct location."""
    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

    response = await client.post("/documents/upload", files=files, headers=auth_headers)
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


@pytest.mark.asyncio
async def test_upload_without_auth_returns_401(client: AsyncClient, cleanup_uploads):
    """Test upload without authentication returns 401."""
    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

    response = await client.post("/documents/upload", files=files)

    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]
