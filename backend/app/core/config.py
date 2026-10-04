import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Base Directory: backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file from backend directory if present
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

class Settings(BaseModel):
    APP_NAME: str = "StudyMate AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    API_PREFIX: str = "/api"
    
    # Server host & port
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    
    # Data Directories
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = BASE_DIR / "data" / "uploads"
    CHROMA_DIR: Path = BASE_DIR / "data" / "chroma"
    
    # AI Credentials (server-side only)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # LLM Models
    GENERATION_MODEL: str = os.getenv("GENERATION_MODEL", "gemini-3.8-flash")
    GEMINI_MODEL_POOL: str = os.getenv(
        "GEMINI_MODEL_POOL", 
        "gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite"
    )

    @property
    def model_pool(self) -> list[str]:
        if os.getenv("GEMINI_MODEL_POOL") is None and os.getenv("GENERATION_MODEL") is not None:
            # If only GENERATION_MODEL is configured, fall back to it for backward compatibility
            return [self.GENERATION_MODEL]
        return [m.strip() for m in self.GEMINI_MODEL_POOL.split(",") if m.strip()]
    # Chunking configuration
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    MIN_CHUNK_SIZE: int = int(os.getenv("MIN_CHUNK_SIZE", "80"))

    # Retrieval configuration
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "8"))

settings = Settings()

# Ensure directories exist
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)

