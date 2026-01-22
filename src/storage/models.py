"""Database models for AuditEng V2.

Uses SQLModel for unified Pydantic + SQLAlchemy models.
All models use table=True to create database tables.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class ValidationStatus(str, Enum):
    """Possible validation result states."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVIEW_NEEDED = "REVIEW_NEEDED"
    PENDING = "PENDING"
    FAILED = "FAILED"


class User(SQLModel, table=True):
    """User account for authentication.

    Supports both web login (email/password) and API access (API keys).
    """

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    documents: list["Document"] = Relationship(back_populates="user")


class Document(SQLModel, table=True):
    """Uploaded PDF document for validation.

    Tracks the original file and its processing status.
    """

    __tablename__ = "documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_hash: str = Field(max_length=64, index=True)  # SHA256
    file_size_bytes: int
    status: str = Field(default="uploaded", max_length=50)  # uploaded, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="documents")
    validation_results: list["ValidationResult"] = Relationship(back_populates="document")


class ValidationResult(SQLModel, table=True):
    """Validation result for a document.

    Stores the verdict, findings, and complete audit trail.
    This is an append-only table for compliance - results are never updated.
    """

    __tablename__ = "validation_results"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True)

    # Verdict
    status: ValidationStatus = Field(default=ValidationStatus.PENDING)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    # Results stored as JSON strings (SQLite doesn't have native JSON)
    findings_json: str | None = Field(default=None)  # JSON array of findings
    evidence_json: str | None = Field(default=None)  # JSON array of evidence
    extraction_result_json: str | None = Field(default=None)  # Full LandingAI response
    analysis_result_json: str | None = Field(default=None)  # Full Claude response

    # Audit trail
    model_version: str | None = Field(default=None, max_length=50)  # e.g., "claude-sonnet-4-5"
    rule_version: str | None = Field(default=None, max_length=50)  # e.g., "2026-01-22"
    processing_time_ms: int | None = Field(default=None)
    error_message: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    document: Document = Relationship(back_populates="validation_results")
