"""Integration tests for authentication with existing endpoints."""

import io
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
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


async def cleanup_user(db_session: AsyncSession, email: str):
    """Clean up user and related sessions."""
    await db_session.execute(delete(Session).where(Session.user_id.in_(
        select(User.id).where(User.email == email)
    )))
    await db_session.execute(delete(User).where(User.email == email))
    await db_session.commit()


async def create_user_with_token(
    db_session: AsyncSession,
    email: str,
    password: str = "testpass123",
    is_superuser: bool = False,
    must_change_password: bool = False,
) -> tuple[User, str]:
    """Create a user and return with auth token."""
    await cleanup_user(db_session, email)

    user = User(
        id=uuid4(),
        email=email,
        hashed_password=hash_password(password),
        is_active=True,
        is_superuser=is_superuser,
        failed_login_attempts=0,
        must_change_password=must_change_password,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create token and session
    token, expires_at = create_access_token(
        user_id=user.id,
        email=user.email,
        is_admin=user.is_superuser,
        remember_me=False,
    )
    session = Session(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=expires_at,
        is_revoked=False,
    )
    db_session.add(session)
    await db_session.commit()

    return user, token


class TestDocumentAuthIntegration:
    """Tests for document endpoints with auth."""

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, client: AsyncClient):
        """Document upload without auth returns 401."""
        files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

        response = await client.post("/documents/upload", files=files)

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_with_auth_succeeds(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Document upload with auth succeeds."""
        user, token = await create_user_with_token(db_session, "upload_test@example.com")

        files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

        response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        assert response.json()["filename"] == "test.pdf"

    @pytest.mark.asyncio
    async def test_extract_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        """Document extraction without auth returns 401."""
        # Create a document with auth first
        user, token = await create_user_with_token(db_session, "extract_auth_test@example.com")

        files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
        upload_response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        doc_id = upload_response.json()["id"]

        # Try extraction without auth
        response = await client.post(f"/documents/{doc_id}/extract")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cannot_access_other_users_document(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User cannot access another user's document."""
        # User 1 uploads document
        user1, token1 = await create_user_with_token(db_session, "user1@example.com")
        files = {"file": ("user1.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
        upload_response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token1}"},
        )
        doc_id = upload_response.json()["id"]

        # User 2 tries to extract it
        user2, token2 = await create_user_with_token(db_session, "user2@example.com")
        response = await client.post(
            f"/documents/{doc_id}/extract",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_can_access_any_document(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Admin can access any user's document."""
        # Regular user uploads document
        user, token = await create_user_with_token(db_session, "regular@example.com")
        files = {"file": ("regular.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
        upload_response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        doc_id = upload_response.json()["id"]

        # Admin can access (extraction may fail due to external API, but auth should pass)
        admin, admin_token = await create_user_with_token(
            db_session, "admin@example.com", is_superuser=True
        )
        response = await client.post(
            f"/documents/{doc_id}/extract",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # 503 means auth passed but LandingAI key not configured - that's expected
        # 403 would mean access denied which is what we're testing against
        assert response.status_code != 403


class TestMustChangePasswordBlocking:
    """Tests for must_change_password enforcement."""

    @pytest.mark.asyncio
    async def test_must_change_blocks_document_upload(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User with must_change_password cannot upload documents."""
        user, token = await create_user_with_token(
            db_session, "mustchange@example.com", must_change_password=True
        )

        files = {"file": ("blocked.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

        response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "password change required" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_must_change_allows_password_change(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User with must_change_password can change password."""
        user, token = await create_user_with_token(
            db_session, "mustchange_allow@example.com",
            password="temppass123",
            must_change_password=True
        )

        response = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "temppass123",
                "new_password": "newpermanent123",
            },
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_after_password_change_can_upload(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """After changing password, user can upload."""
        user, token1 = await create_user_with_token(
            db_session, "mustchange_after@example.com",
            password="temppass123",
            must_change_password=True
        )

        # Change password
        await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "current_password": "temppass123",
                "new_password": "newpermanent123",
            },
        )

        # Login again with new password
        login_response = await client.post(
            "/auth/login",
            json={"email": "mustchange_after@example.com", "password": "newpermanent123"},
        )
        token2 = login_response.json()["access_token"]

        # Now upload should work
        files = {"file": ("unblocked.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

        response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert response.status_code == 201


class TestSessionValidation:
    """Tests for session-based token validation."""

    @pytest.mark.asyncio
    async def test_revoked_session_blocks_access(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Revoked session token is rejected."""
        user, token = await create_user_with_token(db_session, "revoke_test@example.com")

        # Logout (revokes session)
        await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Try to use revoked token
        files = {"file": ("revoked.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

        response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client: AsyncClient):
        """Invalid JWT token is rejected."""
        files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}

        response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401


class TestValidationAuthIntegration:
    """Tests for validation endpoint with auth."""

    @pytest.mark.asyncio
    async def test_validate_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        """Validation without auth returns 401."""
        # Create a document first
        user, token = await create_user_with_token(db_session, "validate_auth@example.com")

        files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
        upload_response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        doc_id = upload_response.json()["id"]

        # Try to validate without auth
        response = await client.post(f"/documents/{doc_id}/validate")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_validate_other_user_document_denied(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User cannot validate another user's document."""
        # User 1 uploads
        user1, token1 = await create_user_with_token(db_session, "validate_user1@example.com")
        files = {"file": ("user1_validate.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
        upload_response = await client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token1}"},
        )
        doc_id = upload_response.json()["id"]

        # User 2 tries to validate
        user2, token2 = await create_user_with_token(db_session, "validate_user2@example.com")
        response = await client.post(
            f"/documents/{doc_id}/validate",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
