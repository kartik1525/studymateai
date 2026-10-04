import json
import re
import logging
from fastapi import HTTPException

from app.models.quiz import QuizGenerateRequest, QuizResponse, QuizQuestion
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.core.prompts import QUIZ_SYSTEM_PROMPT
from app.services.document_store import DocumentStore

logger = logging.getLogger(__name__)

# Patterns that indicate administrative/assessment content rather than academic content.
# These are used for both chunk filtering and question validation.
ADMIN_PATTERNS = [
    r'\bmarks?\s+distribut',
    r'\bweightage\b',
    r'\binternal\s+assessment\b',
    r'\bexternal\s+assessment\b',
    r'\bpassing\s+marks?\b',
    r'\bexamination\s+pattern\b',
    r'\bexam\s+pattern\b',
    r'\bquestion[\s-]*paper\s+pattern\b',
    r'\bteaching\s+hours?\b',
    r'\bnumber\s+of\s+periods?\b',
    r'\bperiods?\s+allocated\b',
    r'\bcourse\s+code\b',
    r'\bsubject\s+code\b',
    r'\bacademic\s+session\b',
    r'\btheory\s+marks?\b',
    r'\bpractical\s+marks?\b',
    r'\bexamination\s+duration\b',
    r'\bgrading\s+(scheme|system|criteria)\b',
    r'\bcarr(?:y|ies)\s+\d+\s+marks?\b',
    r'\b\d+\s+marks?\s+in\s+the\b',
    r'\bmarks?\s+(?:in|for)\s+(?:the\s+)?(?:practical|theory)\b',
    r'\bpractical\s+examination\b',
]

# Compiled once for performance
_ADMIN_RE = re.compile('|'.join(ADMIN_PATTERNS), re.IGNORECASE)

# Question-level patterns that indicate the question is about administration, not academics.
ADMIN_QUESTION_PATTERNS = [
    r'\bhow\s+many\s+marks\b',
    r'\bwhat\s+(?:is|are)\s+the\s+(?:total\s+)?marks\b',
    r'\bwhat\s+(?:is|are)\s+the\s+(?:total\s+)?weightage\b',
    r'\bwhat\s+(?:percentage|weightage)\b',
    r'\bhow\s+many\s+(?:practical|theory)\s+marks\b',
    r'\bhow\s+many\s+periods\b',
    r'\bwhat\s+is\s+the\s+exam(?:ination)?\s+pattern\b',
    r'\bwhat\s+(?:percentage|proportion)\s+of\s+the\s+exam\b',
    r'\bhow\s+many\s+questions\s+(?:will|would)\s+come\b',
    r'\bmarks?\s+(?:does|do|is|are)\s+.*\b(?:carry|hold|assign|allocat)',
    r'\bmarks?\s+(?:assigned|allocated|allotted)\b',
    r'\bexamination\s+(?:scheme|duration)\b',
    r'\baccording\s+to\s+the\s+(?:syllabus|curriculum|material|document)\b',
    r'\bsyllabus\s+outline\b',
    r'\btopic\s+overview\b',
    r'\blisted\s+in\b',
    r'\bmentioned\s+in\b',
    r'\bincluded\s+in\s+the\s+syllabus\b',
    r'\bcurricular\s+goal\b',
    r'\bcompetency\s+[a-z]?\s*\d+\b',
    r'\bcourse\s+code\b',
    r'\bteaching\s+hours\b',
    r'\bexamination\s+marks\b',
    r'\bassessment\s+structure\b',
    r'\bprescribed\s+book\b',
]

_ADMIN_Q_RE = re.compile('|'.join(ADMIN_QUESTION_PATTERNS), re.IGNORECASE)


def _is_primarily_administrative(text: str) -> bool:
    """
    Check if a chunk of text is primarily about administrative/assessment metadata
    rather than academic content. Uses a threshold approach — a single mention of
    'marks' in otherwise educational text should NOT trigger filtering.
    """
    matches = list(_ADMIN_RE.finditer(text))
    if not matches:
        return False

    # If the text is short (< 200 chars) and has admin patterns, it's likely admin
    if len(text) < 200 and len(matches) >= 1:
        return True
    
    # For longer text, require multiple admin indicators
    return len(matches) >= 2


def _is_administrative_question(text: str) -> bool:
    """Check if a generated quiz question or option contains administrative information."""
    return bool(_ADMIN_Q_RE.search(text))

def is_valid_academic_question(q: QuizQuestion) -> bool:
    if _is_administrative_question(q.question):
        return False
    if q.options:
        for opt in q.options:
            if _is_administrative_question(opt):
                return False
    return True


class QuizService:
    
    @classmethod
    def _format_context(cls, retrieved_chunks: list) -> str:
        """Format the retrieved chunks into a string for the prompt."""
        formatted_parts = []
        for i, chunk in enumerate(retrieved_chunks):
            # Include chapter and page strictly so Gemini can copy it
            meta = f"[Source {i+1} | Chapter: {chunk.chapter_number} | Page: {chunk.page}]"
            formatted_parts.append(f"{meta}\n{chunk.text}")
        return "\n\n".join(formatted_parts)

    @classmethod
    def generate_quiz(cls, request: QuizGenerateRequest) -> QuizResponse:
        # Validate document exists and is processed
        doc = DocumentStore.get(request.document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc.processing_status != "processed":
            raise HTTPException(status_code=400, detail="Document is not fully processed yet")

        # Validate chapters belong to document
        doc_chapter_nums = {ch.chapter_number for ch in doc.chapters}
        for ch in request.chapters:
            if ch not in doc_chapter_nums:
                raise HTTPException(status_code=400, detail=f"Chapter {ch} is not in document")

        # Retrieve Context
        top_k = 15 if request.question_count <= 10 else 25
        retrieved_chunks = RetrievalService.retrieve(
            document_id=request.document_id,
            selected_chapters=request.chapters,
            query="Key concepts, definitions, important facts, summaries",
            top_k=top_k
        )

        if not retrieved_chunks:
            raise HTTPException(
                status_code=400, 
                detail="I couldn't find enough information in the selected material to generate this quiz."
            )

        # Filter out primarily administrative chunks before sending to LLM
        educational_chunks = [
            chunk for chunk in retrieved_chunks
            if not _is_primarily_administrative(chunk.text)
        ]

        if not educational_chunks:
            logger.warning("All retrieved chunks were classified as administrative. Using original set.")
            educational_chunks = retrieved_chunks

        context_str = cls._format_context(educational_chunks)
        valid_sources_set = {(c.chapter_number, c.page) for c in educational_chunks}

        validated_questions = []
        seen_questions = set()
        max_attempts = 3
        attempts = 0
        final_title = "Quiz"

        while len(validated_questions) < request.question_count and attempts < max_attempts:
            missing_count = request.question_count - len(validated_questions)
            
            prompt = QUIZ_SYSTEM_PROMPT.format(
                class_name=doc.class_name,
                subject=doc.subject,
                question_count=missing_count,
                difficulty=request.difficulty.upper(),
                question_types=", ".join([qt.upper() for qt in request.question_types]),
                context=context_str
            )

            try:
                raw_response = LLMService.generate_text(prompt, max_retries=3)
            except Exception as e:
                if attempts > 0:
                    logger.warning(f"Quiz generation LLM failure during regeneration: {e}")
                    break
                if type(e).__name__ == "LLMGenerationError":
                    logger.error(f"Quiz generation LLM pool failure: {e}")
                    raise HTTPException(status_code=502, detail=str(e))
                logger.error(f"Quiz generation LLM failure: {e}")
                raise HTTPException(status_code=500, detail="Failed to generate quiz with AI.")

            # Strip potential markdown code blocks around json
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:]
            if raw_response.endswith("```"):
                raw_response = raw_response[:-3]
            raw_response = raw_response.strip()

            try:
                quiz_data = json.loads(raw_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini output as JSON: {raw_response}")
                if attempts == 0:
                    raise HTTPException(status_code=500, detail="Generated quiz format was invalid.")
                break

            try:
                quiz_response = QuizResponse(**quiz_data)
            except Exception as e:
                logger.error(f"Failed to validate QuizResponse pydantic: {e}")
                if attempts == 0:
                    raise HTTPException(status_code=500, detail="Generated quiz did not match required schema.")
                break

            # Capture title from first successful generation
            if attempts == 0 and quiz_response.title:
                final_title = quiz_response.title

            # Validate source grounding, deduplicate, and reject administrative questions
            for q in quiz_response.questions:
                if len(validated_questions) >= request.question_count:
                    break
                    
                # Deduplication
                normalized_q = q.question.strip().lower()
                if normalized_q in seen_questions:
                    continue

                # Academic validation (checks question and options for syllabus/meta language)
                if not is_valid_academic_question(q):
                    logger.info(f"Rejected non-academic/administrative question: {q.question[:80]}...")
                    continue

                # Grounding check
                if (q.source.chapter, q.source.page) not in valid_sources_set:
                    valid_pages_for_ch = [s[1] for s in valid_sources_set if s[0] == q.source.chapter]
                    if valid_pages_for_ch:
                        q.source.page = valid_pages_for_ch[0]
                    else:
                        continue
                
                seen_questions.add(normalized_q)
                validated_questions.append(q)

            attempts += 1

        if not validated_questions:
             raise HTTPException(
                status_code=400, 
                detail="I couldn't generate enough valid questions from the selected material."
            )

        return QuizResponse(
            title=final_title,
            questions=validated_questions
        )
