import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.document import DocumentMeta, Chapter
from app.services.vector_store import RetrievedChunk
from app.services.quiz_service import _is_primarily_administrative, _is_administrative_question
import json

client = TestClient(app)

@pytest.fixture
def mock_document():
    doc = DocumentMeta(
        document_id="test_doc_123",
        document_name="test.pdf",
        class_name="10",
        subject="Science",
        page_count=20,
        chapters=[
            Chapter(chapter_number=1, chapter_title="Ch 1", start_page=1, end_page=5),
            Chapter(chapter_number=2, chapter_title="Ch 2", start_page=6, end_page=10),
            Chapter(chapter_number=3, chapter_title="Ch 3", start_page=11, end_page=15),
            Chapter(chapter_number=5, chapter_title="Presentation Tools", start_page=16, end_page=20),
        ],
        processing_status="processed"
    )
    with patch("app.services.quiz_service.DocumentStore.get", return_value=doc):
        yield doc

@pytest.fixture
def mock_retrieval():
    # Return chunks from chapter 3 only
    chunks = [
        RetrievedChunk(chunk_id="chunk1", text="Fact 1 from ch3", chapter_number=3, chapter_title="Ch 3", page=11, document_name="test", distance=0.1),
        RetrievedChunk(chunk_id="chunk2", text="Fact 2 from ch3", chapter_number=3, chapter_title="Ch 3", page=12, document_name="test", distance=0.2)
    ]
    with patch("app.services.quiz_service.RetrievalService.retrieve", return_value=chunks) as mock:
        yield mock

@pytest.fixture
def mock_llm():
    mock_response = json.dumps({
        "title": "Chapter 3 Quiz",
        "questions": [
            {
                "question": "What is Fact 1?",
                "type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": "Because it is Fact 1.",
                "source": {"chapter": 3, "page": 11}
            },
            {
                "question": "Is Fact 2 true?",
                "type": "true_false",
                "options": ["True", "False"],
                "correct_answer": 0,
                "explanation": "Because it is Fact 2.",
                "source": {"chapter": 3, "page": 12}
            }
        ]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response) as mock:
        yield mock


def test_quiz_generate_success(mock_document, mock_retrieval, mock_llm):
    response = client.post("/api/quiz/generate", json={
        "document_id": "test_doc_123",
        "chapters": [3],
        "question_count": 5, # We requested 5, but mock returns 2
        "difficulty": "medium",
        "question_types": ["multiple_choice", "true_false"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Chapter 3 Quiz"
    assert len(data["questions"]) == 2
    
    # Check that retrieve was called correctly
    mock_retrieval.assert_called_once_with(
        document_id="test_doc_123",
        selected_chapters=[3],
        query="Key concepts, definitions, important facts, summaries",
        top_k=15
    )

def test_quiz_generate_invalid_document():
    with patch("app.services.quiz_service.DocumentStore.get", return_value=None):
        response = client.post("/api/quiz/generate", json={
            "document_id": "invalid",
            "chapters": [1],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 404

def test_quiz_generate_invalid_chapter(mock_document):
    response = client.post("/api/quiz/generate", json={
        "document_id": "test_doc_123",
        "chapters": [99], # Not in doc
        "question_count": 5,
        "difficulty": "medium",
        "question_types": ["multiple_choice"]
    })
    assert response.status_code == 400
    assert "not in document" in response.json()["detail"]

def test_quiz_generate_no_context(mock_document):
    with patch("app.services.quiz_service.RetrievalService.retrieve", return_value=[]):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 400
        assert "couldn't find enough information" in response.json()["detail"]

def test_quiz_generate_source_hallucination(mock_document, mock_retrieval):
    # LLM returns a source that was not in the retrieved chunks
    mock_response = json.dumps({
        "title": "Bad Quiz",
        "questions": [
            {
                "question": "Hallucinated Fact",
                "type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": "Fake.",
                "source": {"chapter": 99, "page": 999} # completely wrong
            }
        ]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        # Since all questions are discarded, we should get a 400
        assert response.status_code == 400
        assert "couldn't generate enough valid questions" in response.json()["detail"]

def test_quiz_generate_duplicate_questions(mock_document, mock_retrieval):
    # LLM returns duplicates
    mock_response = json.dumps({
        "title": "Dup Quiz",
        "questions": [
            {
                "question": "What is Fact 1?",
                "type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": "Because it is Fact 1.",
                "source": {"chapter": 3, "page": 11}
            },
            {
                "question": "What is Fact 1?", # duplicate!
                "type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": "Because it is Fact 1.",
                "source": {"chapter": 3, "page": 11}
            }
        ]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 200
        # Should deduplicate to 1
        assert len(response.json()["questions"]) == 1


# ── Tests: Administrative Content Filtering ──────────────────────────

def test_administrative_chunk_detection():
    """Test that administrative chunks are correctly identified."""
    # Pure admin text (short, clearly about marks)
    assert _is_primarily_administrative(
        "Presentation tools carry 10 marks in the practical examination."
    ) is True
    
    # Admin text about weightage
    assert _is_primarily_administrative(
        "The weightage for internal assessment is 20 marks."
    ) is True
    
    # Admin text about exam pattern
    assert _is_primarily_administrative(
        "Examination pattern: 30 marks theory, 20 marks practical. Total teaching hours: 40 periods."
    ) is True
    
    # Legitimate educational content
    assert _is_primarily_administrative(
        "Presentation software allows users to create slides containing text, images and multimedia."
    ) is False
    
    # Legitimate educational content that mentions a number
    assert _is_primarily_administrative(
        "A byte consists of 8 bits. A kilobyte is 1024 bytes."
    ) is False
    
    # Long educational text with a single incidental mention of 'marks'
    assert _is_primarily_administrative(
        "The Marksman algorithm is used in computer graphics to draw straight lines. "
        "It calculates the intermediate pixel positions by incrementing the x coordinate. "
        "This is efficient because it avoids floating point operations."
    ) is False


def test_administrative_question_detection():
    """Test that administrative quiz questions are correctly identified."""
    # Administrative questions that MUST be rejected
    assert _is_administrative_question("How many marks does presentation software carry?") is True
    assert _is_administrative_question("What is the weightage of the practical exam?") is True
    assert _is_administrative_question("How many practical marks are allocated?") is True
    assert _is_administrative_question("How many periods are allocated to this chapter?") is True
    assert _is_administrative_question("What is the exam pattern for this subject?") is True
    assert _is_administrative_question("What percentage of the exam is practical?") is True
    
    # Valid academic questions that MUST be accepted
    assert _is_administrative_question("What is the purpose of presentation software?") is False
    assert _is_administrative_question("How many bytes are in a kilobyte?") is False
    assert _is_administrative_question("What is artificial intelligence?") is False
    assert _is_administrative_question("Which feature is used to add animation to an object?") is False


def test_quiz_rejects_administrative_questions(mock_document, mock_retrieval):
    """Quiz must reject questions about marks/assessment and keep academic ones."""
    mock_response = json.dumps({
        "title": "Chapter 5 Quiz",
        "questions": [
            {
                "question": "What can presentation software be used to create?",
                "type": "multiple_choice",
                "options": ["Slides", "Databases", "Networks", "Compilers"],
                "correct_answer": 0,
                "explanation": "Presentation software creates slides.",
                "source": {"chapter": 3, "page": 11}
            },
            {
                "question": "How many marks does the presentation part in practicals hold?",
                "type": "multiple_choice",
                "options": ["5", "10", "15", "20"],
                "correct_answer": 1,
                "explanation": "It carries 10 marks.",
                "source": {"chapter": 3, "page": 12}
            }
        ]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 200
        data = response.json()
        # Only the academic question should survive
        assert len(data["questions"]) == 1
        assert "presentation software" in data["questions"][0]["question"].lower()
        # The admin question about marks must be rejected
        for q in data["questions"]:
            assert "how many marks" not in q["question"].lower()


def test_quiz_chunk_filtering_excludes_admin(mock_document):
    """Primarily administrative chunks should be filtered before reaching the LLM."""
    educational_chunk = RetrievedChunk(
        chunk_id="edu_chunk",
        text="Presentation software allows users to create slides containing text, images and multimedia.",
        chapter_number=5, chapter_title="Presentation Tools",
        page=16, document_name="test", distance=0.1
    )
    admin_chunk = RetrievedChunk(
        chunk_id="admin_chunk",
        text="Presentation tools carry 10 marks in the practical examination.",
        chapter_number=5, chapter_title="Presentation Tools",
        page=17, document_name="test", distance=0.2
    )

    with patch("app.services.quiz_service.RetrievalService.retrieve", return_value=[educational_chunk, admin_chunk]):
        mock_response = json.dumps({
            "title": "Presentation Quiz",
            "questions": [{
                "question": "What can you create with presentation software?",
                "type": "multiple_choice",
                "options": ["Slides", "Databases", "Compilers", "Routers"],
                "correct_answer": 0,
                "explanation": "Slides with text, images and multimedia.",
                "source": {"chapter": 5, "page": 16}
            }]
        })
        with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response) as llm_mock:
            response = client.post("/api/quiz/generate", json={
                "document_id": "test_doc_123",
                "chapters": [5],
                "question_count": 5,
                "difficulty": "medium",
                "question_types": ["multiple_choice"]
            })
            assert response.status_code == 200
            # Verify the LLM was called and the admin chunk was filtered
            called_prompt = llm_mock.call_args[0][0]
            assert "Presentation software allows users" in called_prompt
            assert "10 marks in the practical" not in called_prompt

def test_quiz_generate_fallback_success(mock_document, mock_retrieval):
    """Test that a 503 from the primary model correctly falls back to the next model and succeeds in Quiz generation."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "Fallback Quiz",
        "questions": [{
            "question": "Fallback question?",
            "type": "multiple_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation": "Because fallback.",
            "source": {"chapter": 3, "page": 11}
        }]
    })
    
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
            response = client.post("/api/quiz/generate", json={
                "document_id": "test_doc_123",
                "chapters": [3],
                "question_count": 5,
                "difficulty": "medium",
                "question_types": ["multiple_choice"]
            })
            
        assert response.status_code == 200
        assert response.json()["title"] == "Fallback Quiz"
        assert len(response.json()["questions"]) == 1

# ── Tests: Semantic Validation and Regeneration ────────────────────

def test_rejects_syllabus_referential_question(mock_document, mock_retrieval):
    mock_response = json.dumps({
        "title": "Quiz",
        "questions": [{
            "question": "Which reaction is listed in the syllabus?",
            "type": "multiple_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation": "Because.",
            "source": {"chapter": 3, "page": 11}
        }]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 400
        assert "couldn't generate enough valid questions" in response.json()["detail"]


def test_rejects_competency_question(mock_document, mock_retrieval):
    mock_response = json.dumps({
        "title": "Quiz",
        "questions": [{
            "question": "According to competency C 8.2, which action should students perform?",
            "type": "multiple_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation": "Because.",
            "source": {"chapter": 3, "page": 11}
        }]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 400


def test_rejects_administrative_options(mock_document, mock_retrieval):
    mock_response = json.dumps({
        "title": "Quiz",
        "questions": [{
            "question": "Which of these is a factor?",
            "type": "multiple_choice",
            "options": ["examination marks", "course codes", "teaching hours", "None of these"],
            "correct_answer": 0,
            "explanation": "Because.",
            "source": {"chapter": 3, "page": 11}
        }]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 400


def test_accepts_academic_question(mock_document, mock_retrieval):
    mock_response = json.dumps({
        "title": "Quiz",
        "questions": [{
            "question": "Which type of reaction releases heat into the surroundings?",
            "type": "multiple_choice",
            "options": ["Endothermic", "Exothermic", "Displacement", "Combination"],
            "correct_answer": 1,
            "explanation": "Exothermic reactions release heat.",
            "source": {"chapter": 3, "page": 11}
        }]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 200
        assert len(response.json()["questions"]) == 1


def test_accepts_academic_mcq(mock_document, mock_retrieval):
    mock_response = json.dumps({
        "title": "Quiz",
        "questions": [{
            "question": "Which of the following is an example of oxidation?",
            "type": "multiple_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation": "Because.",
            "source": {"chapter": 3, "page": 11}
        }]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 200
        assert len(response.json()["questions"]) == 1


def test_accepts_valid_periodic_classification_question(mock_document, mock_retrieval):
    mock_response = json.dumps({
        "title": "Quiz",
        "questions": [{
            "question": "Which property generally increases across a period from left to right?",
            "type": "multiple_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation": "Because.",
            "source": {"chapter": 3, "page": 11}
        }]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        assert response.status_code == 200
        assert len(response.json()["questions"]) == 1


def test_true_false_is_conceptual(mock_document, mock_retrieval):
    mock_response = json.dumps({
        "title": "Quiz",
        "questions": [{
            "question": "An exothermic reaction releases heat to its surroundings.",
            "type": "true_false",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation": "Because.",
            "source": {"chapter": 3, "page": 11}
        }]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["true_false"]
        })
        assert response.status_code == 200
        assert len(response.json()["questions"]) == 1


def test_true_false_document_reference_rejected(mock_document, mock_retrieval):
    mock_response = json.dumps({
        "title": "Quiz",
        "questions": [{
            "question": "Exothermic reactions are included in the syllabus.",
            "type": "true_false",
            "options": ["True", "False"],
            "correct_answer": 0,
            "explanation": "Because.",
            "source": {"chapter": 3, "page": 11}
        }]
    })
    with patch("app.services.quiz_service.LLMService.generate_text", return_value=mock_response):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["true_false"]
        })
        assert response.status_code == 400


def test_regenerates_rejected_questions(mock_document, mock_retrieval):
    # First response: 2 valid, 1 invalid (admin)
    response_1 = json.dumps({
        "title": "Quiz 1",
        "questions": [
            {
                "question": "Valid 1",
                "type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": "Because.",
                "source": {"chapter": 3, "page": 11}
            },
            {
                "question": "Valid 2",
                "type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": "Because.",
                "source": {"chapter": 3, "page": 11}
            },
            {
                "question": "Included in the syllabus?",
                "type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": "Because.",
                "source": {"chapter": 3, "page": 11}
            }
        ]
    })
    
    # Second response: 1 valid to make up for the rejected one
    response_2 = json.dumps({
        "title": "Quiz 2",
        "questions": [
            {
                "question": "Valid 3",
                "type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": "Because.",
                "source": {"chapter": 3, "page": 11}
            }
        ]
    })
    
    with patch("app.services.quiz_service.LLMService.generate_text", side_effect=[response_1, response_2]):
        response = client.post("/api/quiz/generate", json={
            "document_id": "test_doc_123",
            "chapters": [3],
            "question_count": 5,
            "difficulty": "medium",
            "question_types": ["multiple_choice"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 3
        # Should keep the title from the first successful generation attempt
        assert data["title"] == "Quiz 1"
