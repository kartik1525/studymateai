"""
Tutor API endpoints.

POST /api/tutor/ask — Ask the AI tutor a question based on selected chapters.

PRD Sections: 12 (AI Tutor)
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException

from app.models.chat import TutorAskRequest, TutorAskResponse
from app.models.document import ProcessingStatus
from app.services.document_store import DocumentStore
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tutor", tags=["Tutor"])

@router.post(
    "/ask",
    response_model=TutorAskResponse,
    summary="Ask a question grounded in specific document chapters",
)
async def ask_tutor(request: TutorAskRequest):
    """
    Ask a question to the AI tutor based on the provided document and chapters.
    """
    # ── Validate Request Content ──
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty or whitespace.")

    if not request.chapters:
        raise HTTPException(status_code=400, detail="At least one chapter must be selected.")

    # ── Validate Document State ──
    doc_meta = DocumentStore.get(request.document_id)
    if not doc_meta:
        raise HTTPException(status_code=404, detail=f"Document '{request.document_id}' not found.")

    if doc_meta.processing_status != ProcessingStatus.PROCESSED:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready for querying. Current status: {doc_meta.processing_status.value}",
        )

    # ── Validate Chapters ──
    available_chapters = {ch.chapter_number for ch in doc_meta.chapters}
    invalid_chapters = set(request.chapters) - available_chapters
    if invalid_chapters:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid chapters selected: {list(invalid_chapters)}. Available chapters: {list(available_chapters)}",
        )

    # ── Execute RAG Pipeline ──
    try:
        response = RAGService.ask_tutor(
            document_meta=doc_meta,
            chapters=request.chapters,
            question=question,
        )
        return response
    except Exception as e:
        # Check if it's the specific LLMGenerationError
        if type(e).__name__ == "LLMGenerationError":
            error_msg = str(e)
            logger.error(f"Tutor API error (LLM pool failed): {error_msg}")
            raise HTTPException(status_code=502, detail=error_msg)
        elif isinstance(e, RuntimeError):
            # e.g., Gemini API key missing, empty generation, or quota exhausted
            error_msg = str(e)
            logger.error(f"Tutor API error: {error_msg}")
            # Identify rate limits/quota easily
            if "429" in error_msg or "quota" in error_msg.lower():
                raise HTTPException(status_code=502, detail=f"AI service quota exceeded. Please try again later. Details: {error_msg}")
            raise HTTPException(status_code=502, detail=f"Failed to generate an answer from the AI service: {error_msg}")
        
        logger.exception("Unexpected error in Tutor API.")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing your request.")
