"""
Retrieval service — the query-side of the RAG pipeline.

Combines embedding generation with chapter-scoped vector search.
Returns retrieved chunks with full metadata but never exposes
internal embedding vectors or ChromaDB details to the caller.

PRD Sections: 12 (AI Tutor), 33 (RAG Requirements)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore, RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieved context piece returned to the caller."""
    text: str
    chapter_number: int
    chapter_title: str
    page: int
    document_name: str
    relevance_score: float  # 0.0–1.0, higher = more relevant


class RetrievalService:
    """
    Chapter-scoped retrieval: embed query → filter by metadata → return chunks.

    Guarantees: if selected_chapters=[2, 3], no result will ever
    come from chapter 1, 4, or any other chapter.
    """

    @classmethod
    def retrieve(
        cls,
        document_id: str,
        selected_chapters: list[int],
        query: str,
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve the most relevant chunks for a query, scoped to
        the selected chapters of a document.

        Args:
            document_id: The document to search within.
            selected_chapters: Chapter numbers the student has selected.
            query: The student's question or search text.
            top_k: Max results (defaults to config RETRIEVAL_TOP_K).

        Returns:
            List of RetrievalResult, sorted by relevance (best first).
        """
        if top_k is None:
            top_k = settings.RETRIEVAL_TOP_K

        if not query.strip():
            logger.warning("Empty query received for document %s", document_id)
            return []

        if not selected_chapters:
            logger.warning("No chapters selected for document %s", document_id)
            return []

        logger.info(
            "Retrieving for document=%s, chapters=%s, query='%s' (top_k=%d)",
            document_id, selected_chapters, query[:80], top_k,
        )

        # Step 1: Embed the query
        query_embedding = EmbeddingService.embed_query(query)

        # Step 2: Metadata-filtered similarity search
        retrieved_chunks = VectorStore.query(
            document_id=document_id,
            query_embedding=query_embedding,
            selected_chapters=selected_chapters,
            top_k=top_k,
        )

        # Step 3: Convert to RetrievalResult (hide internal details)
        results = []
        for chunk in retrieved_chunks:
            # Convert ChromaDB cosine distance to a relevance score (0–1)
            # Cosine distance: 0 = identical, 2 = opposite
            # Relevance: 1 - (distance / 2)
            relevance = max(0.0, min(1.0, 1.0 - (chunk.distance / 2.0)))

            results.append(
                RetrievalResult(
                    text=chunk.text,
                    chapter_number=chunk.chapter_number,
                    chapter_title=chunk.chapter_title,
                    page=chunk.page,
                    document_name=chunk.document_name,
                    relevance_score=round(relevance, 4),
                )
            )

        logger.info(
            "Retrieved %d results for document %s (chapters %s)",
            len(results), document_id, selected_chapters,
        )

        return results
