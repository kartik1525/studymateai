"""
LLM generation service using Google Gemini.

Isolated service for generating answers based on grounded prompts.
"""

from __future__ import annotations

import logging
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMGenerationError(Exception):
    """Raised when all models in the pool fail or a non-transient error occurs."""
    pass


class LLMService:
    """Service to interact with the Gemini API for text generation."""

    _client: genai.Client | None = None

    @classmethod
    def _get_client(cls) -> genai.Client:
        if cls._client is None:
            if not settings.GEMINI_API_KEY:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. "
                    "Add it to backend/.env to enable generation."
                )
            cls._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Initialized Gemini client. Model pool: %s", settings.model_pool)
        return cls._client

    @classmethod
    def generate_text(cls, prompt: str, max_retries: int = 2) -> str:
        """
        Generate text from the provided prompt using the model pool.
        Includes retry logic for transient errors, followed by fallback to the next model.
        """
        import time
        client = cls._get_client()
        logger.info("Sending generation request to Gemini model pool...")
        
        # HTTP status codes that usually indicate a temporary/transient issue
        transient_codes = ["429", "503", "408", "500", "504"]
        
        models = settings.model_pool
        total_models = len(models)
        
        for idx, model in enumerate(models, 1):
            for attempt in range(1, max_retries + 1):
                logger.info(f"Gemini model attempt {attempt}/{max_retries}: {model}")
                try:
                    # Enforce strict text generation with low temperature for grounded answers
                    config = types.GenerateContentConfig(
                        temperature=0.1,
                    )
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config,
                    )
                    if not response.text:
                        raise RuntimeError("Received empty response from Gemini API.")
                    
                    logger.info(f"Gemini generation succeeded using: {model}")
                    return response.text
                
                except Exception as e:
                    error_str = str(e)
                    logger.warning(f"Gemini model {model} failed:\n{error_str}")
                    
                    # Determine if it's transient
                    is_transient = any(code in error_str for code in transient_codes) or "quota" in error_str.lower()
                    
                    if not is_transient:
                        logger.error(f"Gemini model {model} failed with non-transient error.")
                        raise LLMGenerationError(f"Non-transient generation error: {e}") from e
                    
                    if attempt < max_retries:
                        wait_time = attempt  # e.g., 1s, 2s
                        logger.info(f"Retrying model {model} in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
            
            logger.warning(f"All retries for model {model} exhausted.")
            if idx < total_models:
                logger.info("Falling back to next model...")
                
        logger.error("All models in the pool failed.")
        raise LLMGenerationError("The AI tutor is temporarily busy. Please try again in a moment.")
