"""History endpoints for viewing validation history.

Provides paginated list of past validations with filtering capabilities.
"""

import json
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_auth
from src.domain.schemas.history import HistoryListItem, HistoryListResponse
from src.storage.database import get_session
from src.storage.models import Document, User, ValidationResult, ValidationStatus

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: ValidationStatus | None = Query(None, description="Filter by validation status"),
    start_date: date | None = Query(None, description="Filter validations on or after this date"),
    end_date: date | None = Query(None, description="Filter validations on or before this date"),
    document_name: str | None = Query(None, description="Partial match on document filename"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_session),
) -> HistoryListResponse:
    """Get paginated validation history for the authenticated user.

    Admins see all validations, regular users see only their own.

    Supports filtering by:
    - status: APPROVED, REJECTED, REVIEW_NEEDED, PENDING, FAILED
    - start_date/end_date: Date range for validation creation
    - document_name: Case-insensitive partial match on filename

    Filters combine with AND logic.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (1-100)
        status: Filter by validation status
        start_date: Filter validations created on or after this date
        end_date: Filter validations created on or before this date
        document_name: Search document filename (case-insensitive partial match)
        current_user: Authenticated user from JWT
        db: Database session

    Returns:
        HistoryListResponse with paginated validation history
    """
    # Build filter conditions
    conditions = []

    # User ownership filter (unless admin)
    if not current_user.is_superuser:
        conditions.append(Document.user_id == current_user.id)

    # Status filter
    if status is not None:
        conditions.append(ValidationResult.status == status)

    # Date range filters (on ValidationResult.created_at)
    if start_date is not None:
        # Convert date to datetime for comparison (start of day)
        start_datetime = datetime.combine(start_date, time.min)
        conditions.append(ValidationResult.created_at >= start_datetime)

    if end_date is not None:
        # Convert date to datetime for comparison (end of day)
        end_datetime = datetime.combine(end_date, time.max)
        conditions.append(ValidationResult.created_at <= end_datetime)

    # Document name search (case-insensitive partial match)
    if document_name is not None:
        conditions.append(Document.filename.ilike(f"%{document_name}%"))

    # Build base query with join
    base_query = select(ValidationResult).join(
        Document, ValidationResult.document_id == Document.id
    )

    # Apply filters
    if conditions:
        base_query = base_query.where(*conditions)

    # Get total count
    count_query = select(func.count()).select_from(ValidationResult).join(
        Document, ValidationResult.document_id == Document.id
    )
    if conditions:
        count_query = count_query.where(*conditions)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    results_query = (
        base_query.order_by(ValidationResult.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    results = await db.execute(results_query)
    validation_results = results.scalars().all()

    # Build response items
    items: list[HistoryListItem] = []
    for vr in validation_results:
        # Get document to access filename
        doc_result = await db.execute(
            select(Document).where(Document.id == vr.document_id)
        )
        doc = doc_result.scalar_one()

        # Parse findings count if available
        findings_count: int | None = None
        if vr.findings_json:
            try:
                findings = json.loads(vr.findings_json)
                if isinstance(findings, list):
                    findings_count = len(findings)
            except (json.JSONDecodeError, TypeError):
                pass

        items.append(
            HistoryListItem(
                id=vr.id,
                document_id=vr.document_id,
                document_filename=doc.filename,
                status=vr.status,
                created_at=vr.created_at,
                findings_count=findings_count,
            )
        )

    # Calculate pagination flags
    has_next = (offset + page_size) < total
    has_prev = page > 1

    return HistoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=has_next,
        has_prev=has_prev,
    )
