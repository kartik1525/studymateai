"""
Pydantic models for the Tutor API (Chat/Q&A).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

class TutorAskRequest(BaseModel):
    """Request payload for asking the AI tutor a question."""
    document_id: str = Field(..., description="ID of the document to query.")
    chapters: list[int] = Field(..., description="List of chapter numbers to restrict the search to.")
    question: str = Field(..., min_length=1, description="The student's question.")


class TutorAskResponse(BaseModel):
    """Response payload containing the grounded answer from the AI tutor."""
    answer: str = Field(..., description="The conceptual explanation from the AI tutor.")
