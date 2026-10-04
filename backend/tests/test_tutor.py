"""
Tests for the AI Tutor API endpoint and Chapter Isolation.

Updated: Tutor no longer exposes source metadata in the response.
The response contains only { "answer": "..." }.
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.models.document import DocumentMeta, ProcessingStatus, Chapter
from app.services.document_store import DocumentStore
from app.services.retrieval_service import RetrievalResult
from app.services.rag_service import RAGService


client = TestClient(app)

# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_document():
    doc = DocumentMeta(
        document_id="doc_tutor_test",
        document_name="AI_Book.pdf",
        class_name="10",
        subject="AI",
        page_count=20,
        chapters=[
            Chapter(chapter_number=1, chapter_title="Intro", start_page=1, end_page=5),
            Chapter(chapter_number=2, chapter_title="ML", start_page=6, end_page=10),
            Chapter(chapter_number=3, chapter_title="Ethics", start_page=11, end_page=15),
        ],
        processing_status=ProcessingStatus.PROCESSED,
    )
    DocumentStore.save(doc)
    yield doc
    DocumentStore.delete(doc.document_id)


@pytest.fixture
def mock_retrieval_service():
    with patch("app.services.rag_service.RetrievalService.retrieve") as mock:
        yield mock


@pytest.fixture
def mock_llm_service():
    with patch("app.services.rag_service.LLMService.generate_text") as mock:
        yield mock


# ── Tests: Validation & Errors ───────────────────────────────────────

def test_ask_empty_question(mock_document):
    response = client.post("/api/tutor/ask", json={
        "document_id": mock_document.document_id,
        "chapters": [1],
        "question": "   "
    })
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


def test_ask_invalid_document():
    response = client.post("/api/tutor/ask", json={
        "document_id": "doc_missing",
        "chapters": [1],
        "question": "What is AI?"
    })
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_ask_document_not_processed(mock_document):
    mock_document.processing_status = ProcessingStatus.PROCESSING
    DocumentStore.save(mock_document)
    
    response = client.post("/api/tutor/ask", json={
        "document_id": mock_document.document_id,
        "chapters": [1],
        "question": "What is AI?"
    })
    assert response.status_code == 400
    assert "not ready" in response.json()["detail"]


def test_ask_invalid_chapter(mock_document):
    response = client.post("/api/tutor/ask", json={
        "document_id": mock_document.document_id,
        "chapters": [99],
        "question": "What is AI?"
    })
    assert response.status_code == 400
    assert "Invalid chapters selected" in response.json()["detail"]


def test_ask_no_chapters(mock_document):
    response = client.post("/api/tutor/ask", json={
        "document_id": mock_document.document_id,
        "chapters": [],
        "question": "What is AI?"
    })
    assert response.status_code == 400
    assert "At least one chapter" in response.json()["detail"]


# ── Tests: Retrieval & Generation Flow ───────────────────────────────

def test_ask_insufficient_context(mock_document, mock_retrieval_service, mock_llm_service):
    # Setup retrieval to return no chunks
    mock_retrieval_service.return_value = []
    
    response = client.post("/api/tutor/ask", json={
        "document_id": mock_document.document_id,
        "chapters": [1],
        "question": "What is quantum computing?"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "don't have enough information" in data["answer"]
    # Response should NOT contain a "sources" key
    assert "sources" not in data
    
    # Verify LLM was NOT called if there's no context
    mock_llm_service.assert_not_called()


def test_ask_success_no_sources_in_response(mock_document, mock_retrieval_service, mock_llm_service):
    """Tutor response must contain only the answer — no sources exposed."""
    # Setup mock retrieval
    mock_retrieval_service.return_value = [
        RetrievalResult(
            text="Machine learning is a subfield of AI.",
            chapter_number=2,
            chapter_title="ML",
            page=7,
            document_name="AI_Book.pdf",
            relevance_score=0.9
        ),
        RetrievalResult(
            text="Another chunk on the same page.",
            chapter_number=2,
            chapter_title="ML",
            page=7,
            document_name="AI_Book.pdf",
            relevance_score=0.8
        )
    ]
    
    # Setup mock LLM
    mock_llm_service.return_value = "Machine learning is a subfield of Artificial Intelligence."
    
    response = client.post("/api/tutor/ask", json={
        "document_id": mock_document.document_id,
        "chapters": [2],
        "question": "What is machine learning?"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Machine learning is a subfield of Artificial Intelligence."
    
    # The response MUST NOT contain sources
    assert "sources" not in data


def test_ask_conceptual_answer_no_citations(mock_document, mock_retrieval_service, mock_llm_service):
    """Verify the response does not contain page numbers or source citations."""
    mock_retrieval_service.return_value = [
        RetrievalResult(
            text="AI is the ability of machines to perform tasks that require human intelligence.",
            chapter_number=1,
            chapter_title="Intro",
            page=2,
            document_name="AI_Book.pdf",
            relevance_score=0.95
        )
    ]
    
    # Simulate a grade-aware conceptual answer
    mock_llm_service.return_value = (
        "### Definition\n"
        "Artificial Intelligence (AI) is the ability of machines to perform tasks "
        "that normally require human intelligence.\n\n"
        "### In simple words\n"
        "AI allows computers to think and learn like humans.\n\n"
        "### Example\n"
        "A voice assistant like Alexa that understands your question is an example of AI."
    )
    
    response = client.post("/api/tutor/ask", json={
        "document_id": mock_document.document_id,
        "chapters": [1],
        "question": "What is artificial intelligence?"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Answer should be conceptual
    assert "Definition" in data["answer"]
    assert "simple words" in data["answer"]
    assert "Example" in data["answer"]
    
    # Must NOT contain source/citation metadata
    assert "Page 1" not in data["answer"]
    assert "Page 2" not in data["answer"]
    assert "Source:" not in data["answer"]
    assert "sources" not in data


def test_ask_llm_failure(mock_document, mock_retrieval_service, mock_llm_service):
    mock_retrieval_service.return_value = [
        RetrievalResult(
            text="Test text", chapter_number=1, chapter_title="Intro",
            page=1, document_name="AI_Book.pdf", relevance_score=0.9
        )
    ]
    
    # Simulate Gemini API error
    mock_llm_service.side_effect = RuntimeError("API overloaded")
    
    response = client.post("/api/tutor/ask", json={
        "document_id": mock_document.document_id,
        "chapters": [1],
        "question": "Test question"
    })
    
    # API should catch it and return 502
    assert response.status_code == 502
    assert "Failed to generate" in response.json()["detail"]


# ── Tests: RAG Service Chapter Isolation ─────────────────────────────

def test_rag_service_prompt_formatting(mock_document, mock_retrieval_service, mock_llm_service):
    mock_retrieval_service.return_value = [
        RetrievalResult(
            text="Ethics chunk", chapter_number=3, chapter_title="Ethics",
            page=12, document_name="AI_Book.pdf", relevance_score=0.9
        )
    ]
    mock_llm_service.return_value = "Ethical answer"
    
    RAGService.ask_tutor(
        document_meta=mock_document,
        chapters=[2, 3],
        question="What about ethics?"
    )
    
    # Verify the correct prompt was sent to the LLM
    mock_llm_service.assert_called_once()
    called_prompt = mock_llm_service.call_args[0][0]
    
    assert "Class 10" in called_prompt
    assert "studying AI" in called_prompt
    assert "Selected Chapters: Chapter 2: ML, Chapter 3: Ethics" in called_prompt
    assert "What about ethics?" in called_prompt
    # Context should NOT expose page numbers or source labels to the LLM prompt
    # (the new prompt uses [Context N] instead of [Source N | Chapter: X | Page: Y])
    assert "[Context 1]" in called_prompt
    assert "Ethics chunk" in called_prompt

def test_ask_llm_fallback_success(mock_document, mock_retrieval_service):
    """Test that a 503 from the primary model correctly falls back to the next model and succeeds."""
    mock_retrieval_service.return_value = [
        RetrievalResult(
            text="AI chunk", chapter_number=1, chapter_title="Intro",
            page=1, document_name="AI_Book.pdf", relevance_score=0.9
        )
    ]
    
    mock_response = MagicMock()
    mock_response.text = "Fallback answer"
    
    from app.services.llm_service import LLMService
    LLMService._client = None
    
    with patch("app.services.llm_service.genai.Client") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        # Primary fails twice (max_retries), next succeeds
        mock_instance.models.generate_content.side_effect = [
            Exception("503 Service Unavailable"),
            Exception("503 Service Unavailable"),
            mock_response
        ]
        
        with patch("time.sleep"):
            response = client.post("/api/tutor/ask", json={
                "document_id": mock_document.document_id,
                "chapters": [1],
                "question": "Test question"
            })
            
        assert response.status_code == 200
        assert response.json()["answer"] == "Fallback answer"
        assert "sources" not in response.json()
