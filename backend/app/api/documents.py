"""
Document API endpoints.

POST /api/documents/upload   — Upload a PDF with class + subject
GET  /api/documents          — List all documents
GET  /api/documents/{id}     — Get document detail with chapters

PRD Sections: 6 (Upload), 9 (Library), 10 (Chapter Detection)
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks

from app.core.config import settings
from app.models.document import (
    Chapter,
    DocumentDetail,
    DocumentListItem,
    DocumentMeta,
    DocumentUploadResponse,
    ProcessingStatus,
)
from app.services.chapter_service import ChapterService
from app.services.document_store import DocumentStore
from app.services.pdf_service import PDFExtractionError, PDFService

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# ── Constants ───────────────────────────────────────────────────────

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
VALID_CLASSES = {"8", "9", "10", "11", "12"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",  # some browsers send this for PDFs
}


# ── Helpers ──────────────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """
    Create a safe filename:
      - Strip directory separators
      - Replace non-alphanumeric chars (except dot, hyphen, underscore) with underscore
      - Collapse multiple underscores
      - Limit length
    """
    name = Path(name).name  # Strip any directory components
    # Replace unsafe chars
    name = re.sub(r"[^\w.\-]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    if len(name) > 200:
        stem = Path(name).stem[:190]
        suffix = Path(name).suffix
        name = stem + suffix
    return name or "document.pdf"


def _process_document(document_id: str, file_path: Path) -> None:
    """
    Background task: extract text, detect chapters, chunk, embed, and ingest.

    Full pipeline:
      PDF → page text → chapter detection → semantic chunks
      → Gemini embeddings → ChromaDB ingestion

    This runs after the upload response has already been returned.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Mark as processing
        DocumentStore.update_status(document_id, ProcessingStatus.PROCESSING)

        # Step 1: Validate the saved file
        PDFService.validate_file(file_path)

        # Step 2: Extract text page-by-page
        pages = PDFService.extract_pages(file_path)
        page_count = len(pages)
        logger.info("Document %s: extracted %d pages", document_id, page_count)

        # Step 3: Extract PDF built-in TOC (bookmarks)
        toc = PDFService.extract_toc(file_path)

        # Step 4: Detect chapters
        chapters = ChapterService.detect_chapters(pages, toc=toc)
        logger.info("Document %s: detected %d chapters", document_id, len(chapters))

        # Step 5: Get document metadata for chunking
        doc_meta = DocumentStore.get(document_id)
        if doc_meta is None:
            raise RuntimeError(f"Document {document_id} not found in store")

        # Step 6: Chunk the document text (respecting chapter boundaries)
        from app.services.chunking_service import ChunkingService, ChunkConfig
        chunk_config = ChunkConfig(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            min_chunk_size=settings.MIN_CHUNK_SIZE,
        )
        chunks = ChunkingService.chunk_document(
            pages=pages,
            chapters=chapters,
            document_id=document_id,
            document_name=doc_meta.document_name,
            class_name=doc_meta.class_name,
            subject=doc_meta.subject,
            config=chunk_config,
        )
        logger.info("Document %s: created %d chunks", document_id, len(chunks))

        # Step 7: Generate embeddings via Gemini
        from app.services.embedding_service import EmbeddingService
        chunk_texts = [c.text for c in chunks]
        embeddings = EmbeddingService.embed_texts(chunk_texts)
        logger.info("Document %s: generated %d embeddings", document_id, len(embeddings))

        # Step 8: Store in ChromaDB
        from app.services.vector_store import VectorStore
        ingested_count = VectorStore.ingest_chunks(document_id, chunks, embeddings)
        logger.info("Document %s: ingested %d chunks into ChromaDB", document_id, ingested_count)

        # Step 9: Update document metadata with results
        DocumentStore.update_status(
            document_id,
            ProcessingStatus.PROCESSED,
            page_count=page_count,
            chapters=chapters,
        )

    except PDFExtractionError as exc:
        DocumentStore.update_status(
            document_id,
            ProcessingStatus.FAILED,
            error_message=str(exc),
        )
    except Exception as exc:
        logger.exception("Processing failed for document %s", document_id)
        DocumentStore.update_status(
            document_id,
            ProcessingStatus.FAILED,
            error_message=f"Processing error: {exc}",
        )


# ── Endpoints ────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
    summary="Upload a textbook PDF for processing",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF textbook file (max 25 MB)"),
    class_name: str = Form(..., description="Student class, e.g. '10'"),
    subject: str = Form(..., description="Subject name"),
):
    """
    Upload a PDF, validate it, save to disk, and trigger background processing.

    The response is returned immediately with status 'uploaded'.
    Processing (text extraction, chapter detection) runs asynchronously.
    Poll GET /api/documents/{document_id} for the processing_status field.
    """
    # ── Validate class ──
    if class_name not in VALID_CLASSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid class '{class_name}'. Supported: {sorted(VALID_CLASSES)}",
        )

    # ── Validate subject ──
    subject = subject.strip()
    if not subject:
        raise HTTPException(status_code=400, detail="Subject name is required.")

    # ── Validate file type ──
    original_name = file.filename or "unknown.pdf"
    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a file with a .pdf extension.",
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type '{file.content_type}'. Expected a PDF file.",
        )

    # ── Read file content and validate size ──
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({len(content) / (1024*1024):.1f} MB) exceeds the 25 MB limit.",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # ── Save to disk ──
    safe_name = _sanitize_filename(original_name)
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    file_path = settings.UPLOADS_DIR / f"{document_id}_{safe_name}"

    file_path.write_bytes(content)

    # ── Create initial metadata record ──
    doc_meta = DocumentMeta(
        document_id=document_id,
        document_name=safe_name,
        class_name=class_name,
        subject=subject,
        processing_status=ProcessingStatus.UPLOADED,
    )
    DocumentStore.save(doc_meta)

    # ── Queue background processing ──
    background_tasks.add_task(_process_document, document_id, file_path)

    return DocumentUploadResponse(
        document_id=document_id,
        document_name=safe_name,
        processing_status=ProcessingStatus.UPLOADED,
    )


@router.get(
    "",
    response_model=list[DocumentListItem],
    summary="List all uploaded documents",
)
async def list_documents():
    """Return all documents in the library, newest first."""
    docs = DocumentStore.list_all()
    return [
        DocumentListItem(
            document_id=d.document_id,
            document_name=d.document_name,
            class_name=d.class_name,
            subject=d.subject,
            page_count=d.page_count,
            chapter_count=len(d.chapters),
            processing_status=d.processing_status,
            upload_date=d.upload_date,
        )
        for d in docs
    ]


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get document detail including chapters",
)
async def get_document(document_id: str):
    """Return full document metadata with detected chapters."""
    doc = DocumentStore.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentDetail(
        document_id=doc.document_id,
        document_name=doc.document_name,
        class_name=doc.class_name,
        subject=doc.subject,
        page_count=doc.page_count,
        chapters=doc.chapters,
        processing_status=doc.processing_status,
        error_message=doc.error_message,
        upload_date=doc.upload_date,
    )
