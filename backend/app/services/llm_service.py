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
            logger.info("Initialized Gemini client for generation model: %s", settings.GENERATION_MODEL)
        return cls._client

    @classmethod
    def generate_text(cls, prompt: str, max_retries: int = 3) -> str:
        """
        Generate text from the provided prompt using the configured generation model.
        Includes simple retry logic for 503 Unavailable errors.
        """
        import time
        client = cls._get_client()
        logger.info("Sending generation request to Gemini...")
        
        for attempt in range(max_retries):
            try:
                # Enforce strict text generation with low temperature for grounded answers
                config = types.GenerateContentConfig(
                    temperature=0.1,
                )
                response = client.models.generate_content(
                    model=settings.GENERATION_MODEL,
                    contents=prompt,
                    config=config,
                )
                if not response.text:
                    raise RuntimeError("Received empty response from Gemini API.")
                return response.text
            except Exception as e:
                error_str = str(e)
                if "503" in error_str and attempt < max_retries - 1:
                    logger.warning(f"Gemini API 503 error on attempt {attempt+1}. Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                logger.error(f"Gemini API generation failed: {e}")
                raise RuntimeError(f"Gemini generation failed: {e}") from e
