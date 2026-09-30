"""
Unit tests for the RAG pipeline (Chunking, Embedding, VectorStore, Retrieval).
"""

from __future__ import annotations

import os
import pytest
from pathlib import Path

from app.models.document import Chapter
from app.services.pdf_service import PageText
from app.services.chunking_service import ChunkingService, ChunkConfig, TextChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.retrieval_service import RetrievalService


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_pages():
    return [
        PageText(1, "This is page 1 content. It talks about AI foundations.\n\nMore foundation stuff."),
        PageText(2, "Page 2 content. Deep learning basics."),
        PageText(3, "Page 3. Ethics in AI. Very important."),
        PageText(4, "Page 4. More ethics."),
    ]

@pytest.fixture
def sample_chapters():
    return [
        Chapter(chapter_number=1, chapter_title="Foundations", start_page=1, end_page=2),
        Chapter(chapter_number=2, chapter_title="Ethics", start_page=3, end_page=4),
    ]


@pytest.fixture(autouse=True)
def _patch_chroma_dir(tmp_path):
    """Ensure ChromaDB uses a temporary directory for tests."""
    from app.core import config as config_module
    
    original_chroma_dir = config_module.settings.CHROMA_DIR
    test_chroma = tmp_path / "chroma"
    test_chroma.mkdir(parents=True)
    
    config_module.settings.CHROMA_DIR = test_chroma
    
    # Reset VectorStore client so it picks up the new path
    VectorStore._client = None
    
    yield
    
    config_module.settings.CHROMA_DIR = original_chroma_dir
    VectorStore._client = None


# ── Chunking Tests ───────────────────────────────────────────────────

def test_chunking_metadata_correctness(sample_pages, sample_chapters):
    config = ChunkConfig(chunk_size=50, chunk_overlap=10, min_chunk_size=10)
    
    chunks = ChunkingService.chunk_document(
        pages=sample_pages,
        chapters=sample_chapters,
        document_id="doc_123",
        document_name="test.pdf",
        class_name="10",
        subject="AI",
        config=config,
    )
    
    assert len(chunks) > 0
    
    # Verify metadata invariants
    for chunk in chunks:
        assert chunk.document_id == "doc_123"
        assert chunk.document_name == "test.pdf"
        assert chunk.class_name == "10"
        assert chunk.subject == "AI"
        assert chunk.chapter_number in (1, 2)
        assert chunk.chapter_title in ("Foundations", "Ethics")
        assert chunk.page in (1, 2, 3, 4)
        assert chunk.chunk_id.startswith("chunk_")


def test_chunking_chapter_boundaries(sample_pages, sample_chapters):
    # Use a large chunk size to ensure it WOULD cross boundaries if allowed
    config = ChunkConfig(chunk_size=1000, chunk_overlap=0, min_chunk_size=10)
    
    chunks = ChunkingService.chunk_document(
        pages=sample_pages,
        chapters=sample_chapters,
        document_id="doc_123",
        document_name="test.pdf",
        class_name="10",
        subject="AI",
        config=config,
    )
    
    # Should produce exactly 2 chunks, one for each chapter, because it can't cross
    assert len(chunks) == 2
    
    chunk_ch1 = next(c for c in chunks if c.chapter_number == 1)
    chunk_ch2 = next(c for c in chunks if c.chapter_number == 2)
    
    # Chapter 1 chunk should not contain Chapter 2 text
    assert "Ethics" not in chunk_ch1.text
    # Chapter 2 chunk should not contain Chapter 1 text
    assert "Foundations" not in chunk_ch2.text


# ── Vector Store & Retrieval Tests ───────────────────────────────────

@pytest.fixture
def mock_embeddings():
    """Mock embeddings to avoid hitting Gemini API during unit tests."""
    return [
        [0.1] * 768,  # Fake embedding 1
        [0.2] * 768,  # Fake embedding 2
        [0.3] * 768,  # Fake embedding 3
        [0.4] * 768,  # Fake embedding 4
    ]


@pytest.fixture
def populated_vector_store(mock_embeddings):
    chunks = [
        TextChunk("c1", "AI is cool", "doc_A", "docA.pdf", "10", "AI", 1, "Intro", 1),
        TextChunk("c2", "Machine learning is a subset", "doc_A", "docA.pdf", "10", "AI", 1, "Intro", 2),
        TextChunk("c3", "Ethics are important", "doc_A", "docA.pdf", "10", "AI", 2, "Ethics", 3),
        TextChunk("c4", "Bias in data", "doc_A", "docA.pdf", "10", "AI", 2, "Ethics", 4),
    ]
    
    VectorStore.ingest_chunks("doc_A", chunks, mock_embeddings)
    return "doc_A"


def test_retrieval_chapter_filtering(populated_vector_store):
    # Query embedding
    query_emb = [0.15] * 768
    
    # Restrict to Chapter 1
    results_ch1 = VectorStore.query("doc_A", query_emb, selected_chapters=[1])
    assert len(results_ch1) > 0
    for res in results_ch1:
        assert res.chapter_number == 1
        
    # Restrict to Chapter 2
    results_ch2 = VectorStore.query("doc_A", query_emb, selected_chapters=[2])
    assert len(results_ch2) > 0
    for res in results_ch2:
        assert res.chapter_number == 2
        
    # Query both
    results_both = VectorStore.query("doc_A", query_emb, selected_chapters=[1, 2])
    assert len(results_both) == 4


def test_retrieval_document_filtering(populated_vector_store, mock_embeddings):
    # Ingest a second document
    chunks_B = [
        TextChunk("c5", "Different topic", "doc_B", "docB.pdf", "10", "AI", 1, "Other", 1)
    ]
    VectorStore.ingest_chunks("doc_B", chunks_B, [mock_embeddings[0]])
    
    query_emb = [0.1] * 768
    
    # Query doc_A
    results_A = VectorStore.query("doc_A", query_emb, selected_chapters=[1, 2])
    for res in results_A:
        assert res.document_name == "docA.pdf"
        assert res.chunk_id in ("c1", "c2", "c3", "c4")
        
    # Query doc_B
    results_B = VectorStore.query("doc_B", query_emb, selected_chapters=[1])
    assert len(results_B) == 1
    assert results_B[0].document_name == "docB.pdf"
    assert results_B[0].chunk_id == "c5"


def test_retrieval_empty_results(populated_vector_store):
    query_emb = [0.9] * 768
    
    # Querying a non-existent chapter should return empty
    results = VectorStore.query("doc_A", query_emb, selected_chapters=[99])
    assert len(results) == 0
    
    # Querying a non-existent document should return empty
    results_doc = VectorStore.query("doc_UNKNOWN", query_emb, selected_chapters=[1])
    assert len(results_doc) == 0


def test_retrieval_service_flow(monkeypatch, populated_vector_store):
    # Mock the embedding service to return a fake embedding for the query
    def mock_embed_query(query):
        return [0.25] * 768
        
    monkeypatch.setattr(EmbeddingService, "embed_query", mock_embed_query)
    
    results = RetrievalService.retrieve("doc_A", [2], "tell me about ethics")
    
    assert len(results) > 0
    for res in results:
        assert res.chapter_number == 2
        assert res.chapter_title == "Ethics"
        assert res.relevance_score > 0.0
