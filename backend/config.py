import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Settings:
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Model configurations
    # Model configurations (Groq supported)
    OCR_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    EXTRACTION_MODEL: str = "llama-3.3-70b-versatile"
    DIET_MODEL: str = "llama-3.3-70b-versatile"
    CHAT_MODEL: str = "llama-3.3-70b-versatile"
    
    # File upload settings
    UPLOAD_DIR: Path = Path("uploads")
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".jpg", ".jpeg", ".png"}
    
    # Vector DB settings
    CHROMA_PERSIST_DIR: Path = Path("./chroma_db")
    COLLECTION_NAME: str = "medical_reports"
    
    def __init__(self):
        # Validate required settings
        if not self.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY not set in environment variables")
        
        # Create necessary directories
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        self.CHROMA_PERSIST_DIR.mkdir(exist_ok=True)

settings = Settings()