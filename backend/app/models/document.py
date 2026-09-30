"""
Pydantic models for document and chapter metadata.

Matches PRD Section 8 — Metadata Model.
"""

from __future__ import annotations

import enum
from datetime import datetime
from pydantic import BaseModel, Field


class ProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Chapter(BaseModel):
    """A single detected chapter within a document."""
    chapter_number: int = Field(..., description="Sequential chapter number (1-indexed)")
    chapter_title: str = Field(..., description="Detected chapter title")
    start_page: int = Field(..., description="First page of the chapter (1-indexed)")
    end_page: int = Field(..., description="Last page of the chapter (1-indexed, inclusive)")


class DocumentMeta(BaseModel):
    """
    Full metadata for an uploaded and processed document.
    Persisted to the document store as JSON.
    """
    document_id: str = Field(..., description="Unique document identifier")
    document_name: str = Field(..., description="Sanitized original filename")
    class_name: str = Field(..., description="Student class, e.g. '10'")
    subject: str = Field(..., description="Subject name, e.g. 'Artificial Intelligence'")
    page_count: int = Field(0, description="Total number of pages in the PDF")
    chapters: list[Chapter] = Field(default_factory=list, description="Detected chapter list")
    processing_status: ProcessingStatus = Field(
        ProcessingStatus.UPLOADED,
        description="Current processing state",
    )
    error_message: str | None = Field(None, description="Error details if processing failed")
    upload_date: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO-8601 upload timestamp",
    )


class DocumentUploadResponse(BaseModel):
    """Response returned immediately after a successful upload trigger."""
    document_id: str
    document_name: str
    processing_status: ProcessingStatus


class DocumentListItem(BaseModel):
    """Compact representation for the document library listing."""
    document_id: str
    document_name: str
    class_name: str
    subject: str
    page_count: int
    chapter_count: int
    processing_status: ProcessingStatus
    upload_date: str


class DocumentDetail(BaseModel):
    """Full detail view returned by GET /api/documents/{document_id}."""
    document_id: str
    document_name: str
    class_name: str
    subject: str
    page_count: int
    chapters: list[Chapter]
    processing_status: ProcessingStatus
    error_message: str | None = None
    upload_date: str
