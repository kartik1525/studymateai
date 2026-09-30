"""
Vector store service using ChromaDB.

Handles:
  - Collection management (one collection per document)
  - Chunk ingestion (text + embedding + metadata)
  - Metadata-filtered similarity search
  - Chapter-scoped retrieval (the critical PRD invariant)

PRD Sections: 8 (Metadata), 32 (RAG Metadata), 33 (RAG Requirements)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import chromadb

from app.core.config import settings
from app.services.chunking_service import TextChunk

logger = logging.getLogger(__name__)

# Default number of results to return from similarity search
DEFAULT_TOP_K = 8


@dataclass
class RetrievedChunk:
    """A chunk returned from vector similarity search."""
    chunk_id: str
    text: str
    chapter_number: int
    chapter_title: str
    page: int
    document_name: str
    distance: float  # Lower = more similar (ChromaDB uses L2 by default)


class VectorStore:
    """ChromaDB-backed vector store with chapter-scoped retrieval."""

    _client: chromadb.PersistentClient | None = None

    @classmethod
    def _get_client(cls) -> chromadb.PersistentClient:
        if cls._client is None:
            chroma_path = str(settings.CHROMA_DIR)
            cls._client = chromadb.PersistentClient(path=chroma_path)
            logger.info("Initialized ChromaDB persistent client at: %s", chroma_path)
        return cls._client

    @classmethod
    def _collection_name(cls, document_id: str) -> str:
        """Each document gets its own collection for clean isolation."""
        # ChromaDB collection names: 3-63 chars, alphanumeric + underscores/hyphens
        return f"doc_{document_id.replace('doc_', '')}"

    # ── Ingestion ───────────────────────────────────────────────────

    @classmethod
    def ingest_chunks(
        cls,
        document_id: str,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> int:
        """
        Store chunks with their embeddings and metadata in ChromaDB.

        Returns the number of chunks ingested.
        """
        if not chunks:
            logger.warning("No chunks to ingest for document %s", document_id)
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings"
            )

        client = cls._get_client()
        col_name = cls._collection_name(document_id)

        # Delete existing collection if re-ingesting
        try:
            client.delete_collection(col_name)
            logger.info("Deleted existing collection: %s", col_name)
        except Exception:
            pass

        collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},  # cosine similarity
        )

        # Prepare batch data
        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "document_id": c.document_id,
                "document_name": c.document_name,
                "class": c.class_name,
                "subject": c.subject,
                "chapter_number": c.chapter_number,
                "chapter_title": c.chapter_title,
                "page": c.page,
            }
            for c in chunks
        ]

        # ChromaDB supports batches up to ~5000; chunk if needed
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end],
            )

        logger.info(
            "Ingested %d chunks into collection '%s' for document %s",
            len(chunks), col_name, document_id,
        )
        return len(chunks)

    # ── Retrieval ───────────────────────────────────────────────────

    @classmethod
    def query(
        cls,
        document_id: str,
        query_embedding: list[float],
        selected_chapters: list[int],
        top_k: int = DEFAULT_TOP_K,
    ) -> list[RetrievedChunk]:
        """
        Perform metadata-filtered similarity search.

        CRITICAL: Filters by document_id AND chapter_number IN selected_chapters.
        This ensures no content from unselected chapters is ever returned.

        Args:
            document_id: The document to search within.
            query_embedding: The embedding vector for the user's query.
            selected_chapters: List of chapter numbers to scope the search.
            top_k: Maximum number of results to return.

        Returns:
            List of RetrievedChunk sorted by relevance (most similar first).
        """
        client = cls._get_client()
        col_name = cls._collection_name(document_id)

        try:
            collection = client.get_collection(col_name)
        except Exception:
            logger.warning("Collection not found: %s", col_name)
            return []

        # Build the metadata filter
        # ChromaDB where clause: document_id must match AND chapter_number
        # must be in the selected list
        if len(selected_chapters) == 1:
            where_filter = {
                "$and": [
                    {"document_id": {"$eq": document_id}},
                    {"chapter_number": {"$eq": selected_chapters[0]}},
                ]
            }
        else:
            where_filter = {
                "$and": [
                    {"document_id": {"$eq": document_id}},
                    {"chapter_number": {"$in": selected_chapters}},
                ]
            }

        logger.info(
            "Querying collection '%s': chapters=%s, top_k=%d",
            col_name, selected_chapters, top_k,
        )

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Parse results
        retrieved: list[RetrievedChunk] = []
        if results and results["ids"] and results["ids"][0]:
            for idx, chunk_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][idx]
                retrieved.append(
                    RetrievedChunk(
                        chunk_id=chunk_id,
                        text=results["documents"][0][idx],
                        chapter_number=meta["chapter_number"],
                        chapter_title=meta["chapter_title"],
                        page=meta["page"],
                        document_name=meta["document_name"],
                        distance=results["distances"][0][idx],
                    )
                )

        logger.info("Retrieved %d chunks from collection '%s'", len(retrieved), col_name)
        return retrieved

    # ── Cleanup ─────────────────────────────────────────────────────

    @classmethod
    def delete_document(cls, document_id: str) -> bool:
        """Delete the entire collection for a document."""
        client = cls._get_client()
        col_name = cls._collection_name(document_id)
        try:
            client.delete_collection(col_name)
            logger.info("Deleted collection: %s", col_name)
            return True
        except Exception:
            return False

    @classmethod
    def get_chunk_count(cls, document_id: str) -> int:
        """Return the number of chunks stored for a document."""
        client = cls._get_client()
        col_name = cls._collection_name(document_id)
        try:
            collection = client.get_collection(col_name)
            return collection.count()
        except Exception:
            return 0
