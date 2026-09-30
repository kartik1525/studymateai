"""
RAG Service.

Orchestrates retrieval of relevant chunks and generation of grounded answers.
Handles insufficient context detection and deduplication of source references.
"""

from __future__ import annotations

import logging

from app.models.chat import TutorAskResponse, SourceReference
from app.models.document import DocumentMeta
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.core.prompts import TUTOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class RAGService:
    """Service to orchestrate the Retrieval-Augmented Generation flow."""

    INSUFFICIENT_CONTEXT_MESSAGE = "I couldn't find enough information about this in the selected material."

    @classmethod
    def ask_tutor(
        cls,
        document_meta: DocumentMeta,
        chapters: list[int],
        question: str,
    ) -> TutorAskResponse:
        """
        Answers a student's question based on retrieved document chunks.
        
        Args:
            document_meta: Metadata of the document to query.
            chapters: List of chapter numbers to restrict the search to.
            question: The student's question.
            
        Returns:
            TutorAskResponse containing the answer and source references.
        """
        # Step 1: Retrieve relevant chunks
        logger.info(f"Retrieving chunks for doc '{document_meta.document_id}', chapters {chapters}")
        retrieved_chunks = RetrievalService.retrieve(
            document_id=document_meta.document_id,
            selected_chapters=chapters,
            query=question,
        )

        # Step 2: Handle insufficient context (no results from retrieval)
        if not retrieved_chunks:
            logger.info("No relevant chunks retrieved. Returning fallback message.")
            return TutorAskResponse(
                answer=cls.INSUFFICIENT_CONTEXT_MESSAGE,
                sources=[]
            )

        # Step 3: Build the grounded context string
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks):
            # Include chapter and page information explicitly for the LLM
            part = f"[Source {i+1} | Chapter: {chunk.chapter_title} | Page: {chunk.page}]\n{chunk.text}\n"
            context_parts.append(part)
        
        context_text = "\n".join(context_parts)

        # Build chapter titles string for the prompt
        chapter_titles = []
        for ch_num in chapters:
            for doc_ch in document_meta.chapters:
                if doc_ch.chapter_number == ch_num:
                    chapter_titles.append(f"Chapter {ch_num}: {doc_ch.chapter_title}")
                    break
        chapters_str = ", ".join(chapter_titles) if chapter_titles else ", ".join([str(c) for c in chapters])

        # Step 4: Construct the system prompt
        prompt = TUTOR_SYSTEM_PROMPT.format(
            class_name=document_meta.class_name,
            subject=document_meta.subject,
            chapters_str=chapters_str,
            question=question,
            context=context_text,
        )

        # Step 5: Call Gemini LLM
        try:
            logger.info("Calling LLM to generate answer based on retrieved context.")
            answer_text = LLMService.generate_text(prompt)
            
            # Additional safety check on the LLM's output
            if cls.INSUFFICIENT_CONTEXT_MESSAGE.strip().lower() in answer_text.strip().lower():
                # If the LLM returns the exact fallback message, clear the sources
                return TutorAskResponse(
                    answer=cls.INSUFFICIENT_CONTEXT_MESSAGE,
                    sources=[]
                )

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise

        # Step 6: Construct unique source references
        # Ensure we only include sources that were actually retrieved
        unique_sources: dict[str, SourceReference] = {}
        for chunk in retrieved_chunks:
            source_key = f"{chunk.document_name}-{chunk.chapter_title}-{chunk.page}"
            if source_key not in unique_sources:
                unique_sources[source_key] = SourceReference(
                    document=chunk.document_name,
                    chapter=chunk.chapter_title,
                    page=chunk.page
                )
                
        sources_list = list(unique_sources.values())

        return TutorAskResponse(
            answer=answer_text.strip(),
            sources=sources_list,
        )
