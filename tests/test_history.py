"""Tests for history endpoints.

Validates HIST-01 through HIST-04 requirements:
- HIST-01: List history with pagination
- HIST-02: Filter by status, date range, document name
- HIST-04: Detail view with access control
"""

import json
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.services.auth import hash_password
from src.storage.models import Document, User, ValidationResult, ValidationStatus


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a regular test user."""
    # Clean up any existing test user
    result = await db_session.execute(
        select(User).where(User.email == "historyuser@example.com")
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Delete related records first
        await db_session.execute(
            delete(ValidationResult).where(
                ValidationResult.document_id.in_(
                    select(Document.id).where(Document.user_id == existing.id)
                )
            )
        )
        await db_session.execute(
            delete(Document).where(Document.user_id == existing.id)
        )
        await db_session.execute(
            delete(User).where(User.email == "historyuser@example.com")
        )
        await db_session.commit()

    user = User(
        id=uuid4(),
        email="historyuser@example.com",
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
async def admin_user(db_session: AsyncSession):
    """Create an admin user."""
    # Clean up any existing admin
    result = await db_session.execute(
        select(User).where(User.email == "historyadmin@example.com")
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Delete related records first
        await db_session.execute(
            delete(ValidationResult).where(
                ValidationResult.document_id.in_(
                    select(Document.id).where(Document.user_id == existing.id)
                )
            )
        )
        await db_session.execute(
            delete(Document).where(Document.user_id == existing.id)
        )
        await db_session.execute(
            delete(User).where(User.email == "historyadmin@example.com")
        )
        await db_session.commit()

    user = User(
        id=uuid4(),
        email="historyadmin@example.com",
        hashed_password=hash_password("adminpass123"),
        is_active=True,
        is_superuser=True,  # Admin!
        failed_login_attempts=0,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session: AsyncSession):
    """Create another regular user for isolation tests."""
    # Clean up any existing user
    result = await db_session.execute(
        select(User).where(User.email == "otheruser@example.com")
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Delete related records first
        await db_session.execute(
            delete(ValidationResult).where(
                ValidationResult.document_id.in_(
                    select(Document.id).where(Document.user_id == existing.id)
                )
            )
        )
        await db_session.execute(
            delete(Document).where(Document.user_id == existing.id)
        )
        await db_session.execute(
            delete(User).where(User.email == "otheruser@example.com")
        )
        await db_session.commit()

    user = User(
        id=uuid4(),
        email="otheruser@example.com",
        hashed_password=hash_password("otherpass123"),
        is_active=True,
        is_superuser=False,
        failed_login_attempts=0,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def get_auth_token(client: AsyncClient, email: str, password: str) -> str:
    """Helper to get authentication token."""
    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()["access_token"]


async def create_test_document(db_session: AsyncSession, user: User, filename: str = "test-doc.pdf") -> Document:
    """Helper to create a test document."""
    document = Document(
        id=uuid4(),
        user_id=user.id,
        filename=filename,
        file_path=f"/data/uploads/{filename}",
        file_hash="abc123hash",
        file_size_bytes=100000,
        status="completed",
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


async def create_test_validation(
    db_session: AsyncSession,
    document: Document,
    status: ValidationStatus = ValidationStatus.APPROVED,
    findings_count: int = 0,
    created_at: datetime | None = None,
) -> ValidationResult:
    """Helper to create a test validation result."""
    # Create sample findings
    sample_findings = []
    for i in range(findings_count):
        sample_findings.append({
            "rule_id": f"VAL-{i+1:02d}",
            "severity": "ERROR",
            "message": f"Test finding {i+1}",
            "field_name": f"test_field_{i+1}",
            "found_value": "incorrect",
            "expected_value": "correct",
            "location": {
                "page": 0,
                "bbox": {"left": 0.1, "top": 0.2, "right": 0.3, "bottom": 0.4}
            }
        })

    validation = ValidationResult(
        id=uuid4(),
        document_id=document.id,
        status=status,
        findings_json=json.dumps(sample_findings) if findings_count > 0 else None,
        model_version="claude-sonnet-4-5",
        rule_version="2026-01-27",
        processing_time_ms=1500,
    )

    if created_at:
        validation.created_at = created_at

    db_session.add(validation)
    await db_session.commit()
    await db_session.refresh(validation)
    return validation


class TestListHistoryBasic:
    """Tests for HIST-01: Basic list history functionality."""

    @pytest.mark.asyncio
    async def test_list_history_empty(self, client: AsyncClient, test_user):
        """New user sees empty history."""
        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        response = await client.get(
            "/history/",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["has_next"] is False
        assert data["has_prev"] is False

    @pytest.mark.asyncio
    async def test_list_history_with_results(self, client: AsyncClient, test_user, db_session: AsyncSession):
        """User sees their validations."""
        # Create test data
        doc = await create_test_document(db_session, test_user, "report1.pdf")
        await create_test_validation(db_session, doc, ValidationStatus.APPROVED, findings_count=3)

        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        response = await client.get(
            "/history/",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["document_filename"] == "report1.pdf"
        assert data["items"][0]["status"] == "APPROVED"
        assert data["items"][0]["findings_count"] == 3

    @pytest.mark.asyncio
    async def test_list_history_pagination(self, client: AsyncClient, test_user, db_session: AsyncSession):
        """Page and page_size work correctly."""
        # Create 5 test validations
        for i in range(5):
            doc = await create_test_document(db_session, test_user, f"doc{i}.pdf")
            # Create with different timestamps to ensure ordering
            created_at = datetime.utcnow() - timedelta(hours=i)
            await create_test_validation(db_session, doc, ValidationStatus.APPROVED, created_at=created_at)

        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        # Page 1: 2 items
        response = await client.get(
            "/history/?page=1&page_size=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["has_next"] is True
        assert data["has_prev"] is False

        # Page 2: 2 items
        response = await client.get(
            "/history/?page=2&page_size=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 2
        assert data["has_next"] is True
        assert data["has_prev"] is True

        # Page 3: 1 item
        response = await client.get(
            "/history/?page=3&page_size=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        assert len(data["items"]) == 1
        assert data["page"] == 3
        assert data["has_next"] is False
        assert data["has_prev"] is True

    @pytest.mark.asyncio
    async def test_list_history_requires_auth(self, client: AsyncClient):
        """401 without token."""
        response = await client.get("/history/")
        assert response.status_code == 401


class TestListHistoryOwnership:
    """Tests for HIST-01: User isolation and admin access."""

    @pytest.mark.asyncio
    async def test_list_history_user_isolation(self, client: AsyncClient, test_user, other_user, db_session: AsyncSession):
        """User A can't see User B's history."""
        # Create validations for both users
        doc_a = await create_test_document(db_session, test_user, "user_a_doc.pdf")
        await create_test_validation(db_session, doc_a, ValidationStatus.APPROVED)

        doc_b = await create_test_document(db_session, other_user, "user_b_doc.pdf")
        await create_test_validation(db_session, doc_b, ValidationStatus.REJECTED)

        # User A should only see their document
        token_a = await get_auth_token(client, "historyuser@example.com", "testpass123")
        response = await client.get(
            "/history/",
            headers={"Authorization": f"Bearer {token_a}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["document_filename"] == "user_a_doc.pdf"

        # User B should only see their document
        token_b = await get_auth_token(client, "otheruser@example.com", "otherpass123")
        response = await client.get(
            "/history/",
            headers={"Authorization": f"Bearer {token_b}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["document_filename"] == "user_b_doc.pdf"

    @pytest.mark.asyncio
    async def test_list_history_admin_sees_all(self, client: AsyncClient, test_user, admin_user, db_session: AsyncSession):
        """Admin sees all users' history."""
        # Create validations for regular user
        doc_user = await create_test_document(db_session, test_user, "user_doc.pdf")
        await create_test_validation(db_session, doc_user, ValidationStatus.APPROVED)

        # Create validations for admin
        doc_admin = await create_test_document(db_session, admin_user, "admin_doc.pdf")
        await create_test_validation(db_session, doc_admin, ValidationStatus.REVIEW_NEEDED)

        # Admin should see both
        token_admin = await get_auth_token(client, "historyadmin@example.com", "adminpass123")
        response = await client.get(
            "/history/",
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2  # At least the two we created
        filenames = {item["document_filename"] for item in data["items"]}
        assert "user_doc.pdf" in filenames
        assert "admin_doc.pdf" in filenames


class TestHistoryFilters:
    """Tests for HIST-02: Filtering capabilities."""

    @pytest.mark.asyncio
    async def test_filter_by_status(self, client: AsyncClient, test_user, db_session: AsyncSession):
        """Filter by status returns only matching validations."""
        # Create validations with different statuses
        doc1 = await create_test_document(db_session, test_user, "approved.pdf")
        await create_test_validation(db_session, doc1, ValidationStatus.APPROVED)

        doc2 = await create_test_document(db_session, test_user, "rejected.pdf")
        await create_test_validation(db_session, doc2, ValidationStatus.REJECTED)

        doc3 = await create_test_document(db_session, test_user, "review.pdf")
        await create_test_validation(db_session, doc3, ValidationStatus.REVIEW_NEEDED)

        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        # Filter for APPROVED
        response = await client.get(
            "/history/?status=APPROVED",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "APPROVED"
        assert data["items"][0]["document_filename"] == "approved.pdf"

        # Filter for REJECTED
        response = await client.get(
            "/history/?status=REJECTED",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, client: AsyncClient, test_user, db_session: AsyncSession):
        """Start_date and end_date filter works."""
        now = datetime.utcnow()

        # Create validations at different times
        doc1 = await create_test_document(db_session, test_user, "old.pdf")
        await create_test_validation(db_session, doc1, ValidationStatus.APPROVED, created_at=now - timedelta(days=10))

        doc2 = await create_test_document(db_session, test_user, "recent.pdf")
        await create_test_validation(db_session, doc2, ValidationStatus.APPROVED, created_at=now - timedelta(days=2))

        doc3 = await create_test_document(db_session, test_user, "today.pdf")
        await create_test_validation(db_session, doc3, ValidationStatus.APPROVED, created_at=now)

        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        # Filter last 5 days
        start_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")
        response = await client.get(
            f"/history/?start_date={start_date}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # recent and today, not old
        filenames = {item["document_filename"] for item in data["items"]}
        assert "old.pdf" not in filenames
        assert "recent.pdf" in filenames
        assert "today.pdf" in filenames

        # Filter last week only (not today)
        end_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        response = await client.get(
            f"/history/?end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        assert data["total"] == 2  # old and recent, not today
        filenames = {item["document_filename"] for item in data["items"]}
        assert "today.pdf" not in filenames

    @pytest.mark.asyncio
    async def test_filter_by_document_name(self, client: AsyncClient, test_user, db_session: AsyncSession):
        """Partial match search works (case-insensitive)."""
        # Create documents with different names
        doc1 = await create_test_document(db_session, test_user, "Megger_Test_Report.pdf")
        await create_test_validation(db_session, doc1, ValidationStatus.APPROVED)

        doc2 = await create_test_document(db_session, test_user, "Thermography_Report.pdf")
        await create_test_validation(db_session, doc2, ValidationStatus.APPROVED)

        doc3 = await create_test_document(db_session, test_user, "megger_calibration.pdf")
        await create_test_validation(db_session, doc3, ValidationStatus.APPROVED)

        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        # Search for "megger" (case-insensitive)
        response = await client.get(
            "/history/?document_name=megger",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # Both megger files
        filenames = {item["document_filename"] for item in data["items"]}
        assert "Megger_Test_Report.pdf" in filenames
        assert "megger_calibration.pdf" in filenames
        assert "Thermography_Report.pdf" not in filenames

        # Search for "Report"
        response = await client.get(
            "/history/?document_name=Report",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        assert data["total"] == 2  # Both *Report.pdf files

    @pytest.mark.asyncio
    async def test_combined_filters(self, client: AsyncClient, test_user, db_session: AsyncSession):
        """Multiple filters AND together."""
        now = datetime.utcnow()

        # Create various documents
        doc1 = await create_test_document(db_session, test_user, "Megger_Approved.pdf")
        await create_test_validation(db_session, doc1, ValidationStatus.APPROVED, created_at=now - timedelta(days=1))

        doc2 = await create_test_document(db_session, test_user, "Megger_Rejected.pdf")
        await create_test_validation(db_session, doc2, ValidationStatus.REJECTED, created_at=now - timedelta(days=1))

        doc3 = await create_test_document(db_session, test_user, "Thermo_Approved.pdf")
        await create_test_validation(db_session, doc3, ValidationStatus.APPROVED, created_at=now - timedelta(days=1))

        doc4 = await create_test_document(db_session, test_user, "Megger_Approved_Old.pdf")
        await create_test_validation(db_session, doc4, ValidationStatus.APPROVED, created_at=now - timedelta(days=10))

        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        # Filter: status=APPROVED AND document_name=Megger AND recent
        start_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")
        response = await client.get(
            f"/history/?status=APPROVED&document_name=Megger&start_date={start_date}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only Megger_Approved.pdf matches all filters
        assert data["items"][0]["document_filename"] == "Megger_Approved.pdf"


class TestHistoryDetail:
    """Tests for HIST-04: Detail view with access control."""

    @pytest.mark.asyncio
    async def test_get_history_detail(self, client: AsyncClient, test_user, db_session: AsyncSession):
        """Returns full validation with findings."""
        doc = await create_test_document(db_session, test_user, "detail_test.pdf")
        validation = await create_test_validation(db_session, doc, ValidationStatus.REJECTED, findings_count=2)

        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        response = await client.get(
            f"/history/{validation.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(validation.id)
        assert data["status"] == "REJECTED"
        assert data["findings_count"] == 2
        assert len(data["findings"]) == 2
        assert data["document"]["filename"] == "detail_test.pdf"
        assert data["model_version"] == "claude-sonnet-4-5"
        assert data["validator_version"] == "2026-01-27"
        assert data["processing_time_ms"] == 1500

        # Check finding structure
        finding = data["findings"][0]
        assert "rule_id" in finding
        assert "severity" in finding
        assert "message" in finding
        assert "field_name" in finding

    @pytest.mark.asyncio
    async def test_get_history_detail_not_found(self, client: AsyncClient, test_user):
        """404 for invalid ID."""
        fake_id = uuid4()
        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        response = await client.get(
            f"/history/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_history_detail_access_denied(self, client: AsyncClient, test_user, other_user, db_session: AsyncSession):
        """403 for other user's validation."""
        # Create validation for other_user
        doc = await create_test_document(db_session, other_user, "other_doc.pdf")
        validation = await create_test_validation(db_session, doc, ValidationStatus.APPROVED)

        # test_user tries to access it
        token = await get_auth_token(client, "historyuser@example.com", "testpass123")

        response = await client.get(
            f"/history/{validation.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_history_detail_admin_access(self, client: AsyncClient, test_user, admin_user, db_session: AsyncSession):
        """Admin can view any validation."""
        # Create validation for regular user
        doc = await create_test_document(db_session, test_user, "user_doc.pdf")
        validation = await create_test_validation(db_session, doc, ValidationStatus.APPROVED, findings_count=1)

        # Admin can access it
        token_admin = await get_auth_token(client, "historyadmin@example.com", "adminpass123")

        response = await client.get(
            f"/history/{validation.id}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(validation.id)
        assert data["document"]["filename"] == "user_doc.pdf"
