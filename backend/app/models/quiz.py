from pydantic import BaseModel, Field, conint, conlist, model_validator
from typing import Literal

class QuizSource(BaseModel):
    chapter: int = Field(..., description="The chapter number the question is based on")
    page: int = Field(..., description="The page number the question is based on")

class QuizQuestion(BaseModel):
    question: str = Field(..., min_length=5, description="The question text")
    type: Literal["multiple_choice", "true_false"] = Field(..., description="The type of question")
    options: conlist(str, min_length=2, max_length=4) = Field(..., description="The answer options")
    correct_answer: int = Field(..., ge=0, le=3, description="The index of the correct option")
    explanation: str = Field(..., min_length=5, description="Explanation for the correct answer")
    source: QuizSource

    @model_validator(mode='after')
    def validate_options_length(self):
        if self.type == "multiple_choice" and len(self.options) != 4:
            raise ValueError("Multiple choice questions must have exactly 4 options")
        if self.type == "true_false" and len(self.options) != 2:
            raise ValueError("True/False questions must have exactly 2 options")
        if self.correct_answer >= len(self.options):
            raise ValueError(f"correct_answer index {self.correct_answer} out of bounds for options of length {len(self.options)}")
        return self

class QuizResponse(BaseModel):
    title: str = Field(..., description="A title for the generated quiz")
    questions: list[QuizQuestion]

class QuizGenerateRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    chapters: conlist(int, min_length=1) = Field(..., description="List of explicit chapter numbers")
    question_count: Literal[5, 10, 15, 20]
    difficulty: Literal["easy", "medium", "hard"]
    question_types: conlist(Literal["multiple_choice", "true_false"], min_length=1)
