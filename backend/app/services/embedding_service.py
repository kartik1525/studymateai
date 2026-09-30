"""
Embedding service using Google Gemini.

Generates text embeddings for document chunks using Gemini's
text-embedding model. Used during both ingestion and query time.

All Gemini credentials are kept server-side only (PRD Section 36).
"""

from __future__ import annotations

import logging
from google import genai

from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini embedding model
EMBEDDING_MODEL = "models/gemini-embedding-001"
# Maximum batch size for embedding requests
MAX_BATCH_SIZE = 100


class EmbeddingService:
    """Generate embeddings via the Gemini API."""

    _client: genai.Client | None = None

    @classmethod
    def _get_client(cls) -> genai.Client:
        if cls._client is None:
            if not settings.GEMINI_API_KEY:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. "
                    "Add it to backend/.env to enable embeddings."
                )
            cls._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Initialized Gemini client for embedding model: %s", EMBEDDING_MODEL)
        return cls._client

    @classmethod
    def embed_texts(cls, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of text strings.

        Returns a list of float vectors, one per input text.
        Handles batching internally if the input exceeds MAX_BATCH_SIZE.
        """
        if not texts:
            return []

        client = cls._get_client()
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i : i + MAX_BATCH_SIZE]
            logger.info(
                "Generating embeddings: batch %d–%d of %d texts",
                i + 1, min(i + len(batch), len(texts)), len(texts),
            )
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=batch,
            )
            for emb in response.embeddings:
                all_embeddings.append(emb.values)

        logger.info("Generated %d embeddings total", len(all_embeddings))
        return all_embeddings

    @classmethod
    def embed_query(cls, query: str) -> list[float]:
        """Generate a single embedding for a search query."""
        result = cls.embed_texts([query])
        return result[0]
