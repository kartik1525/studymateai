import logging
from fastapi import APIRouter

from app.models.quiz import QuizGenerateRequest, QuizResponse
from app.services.quiz_service import QuizService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quiz", tags=["Quiz"])

@router.post("/generate", response_model=QuizResponse)
def generate_quiz(request: QuizGenerateRequest):
    return QuizService.generate_quiz(request)
