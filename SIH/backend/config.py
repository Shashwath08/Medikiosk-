import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "MediKiosk Patient Experience"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    
    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://localhost:5173",
        "*"
    ]
    
    # File Upload Limits
    UPLOAD_FOLDER: str = str(UPLOAD_DIR)
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    ALLOWED_MIME_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf"
    ]
    
    # Supported Languages (ISO 639-1 code -> Display name)
    SUPPORTED_LANGUAGES: dict[str, str] = {
        "en": "English",
        "hi": "हिंदी (Hindi)",
        "ml": "മലയാളം (Malayalam)",
        "ta": "தமிழ் (Tamil)",
        "kn": "ಕನ್ನಡ (Kannada)",
        "te": "తెలుగు (Telugu)"
    }
    
    # Default Session Expiry or Timeout (minutes)
    SESSION_TIMEOUT_MINUTES: int = 60

settings = Settings()
