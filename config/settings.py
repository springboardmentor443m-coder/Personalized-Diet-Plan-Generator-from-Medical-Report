"""Centralised configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

API_KEY: str = os.getenv("API_KEY", "")

UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_MB: int = 20

DATABASE_PATH: Path = Path(
    os.getenv("DATABASE_PATH", "data/diet_plan.db")
).resolve()

SESSION_TTL_HOURS: int = int(os.getenv("SESSION_TTL_HOURS", "72"))

OCR_VISION_MODEL: str = os.getenv(
    "OCR_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)
EXTRACTION_MODEL: str = os.getenv(
    "EXTRACTION_MODEL", "moonshotai/kimi-k2-instruct"
)

OCR_VISION_MODEL_FALLBACK: str = os.getenv(
    "OCR_VISION_MODEL_FALLBACK", "meta-llama/llama-4-maverick-17b-128e-instruct"
)
EXTRACTION_MODEL_FALLBACK: str = os.getenv(
    "EXTRACTION_MODEL_FALLBACK", "meta-llama/llama-4-scout-17b-16e-instruct"
)

MAX_OCR_WORKERS: int = int(os.getenv("MAX_OCR_WORKERS", "8"))

IMAGE_ENCODE_FORMAT: str = os.getenv("IMAGE_ENCODE_FORMAT", "JPEG")
IMAGE_ENCODE_QUALITY: int = int(os.getenv("IMAGE_ENCODE_QUALITY", "95"))

MAX_EXTRACTION_RETRIES: int = int(os.getenv("MAX_EXTRACTION_RETRIES", "3"))
MAX_OCR_RETRIES: int = int(os.getenv("MAX_OCR_RETRIES", "2"))

INTER_DOCUMENT_DELAY_SECONDS: float = float(
    os.getenv("INTER_DOCUMENT_DELAY_SECONDS", "2.0")
)
RATE_LIMIT_RETRY_DELAY_SECONDS: float = float(
    os.getenv("RATE_LIMIT_RETRY_DELAY_SECONDS", "15.0")
)

MAX_DOCUMENTS_PER_SESSION: int = int(
    os.getenv("MAX_DOCUMENTS_PER_SESSION", "10")
)

CONFLICT_THRESHOLD_PERCENT: float = float(
    os.getenv("CONFLICT_THRESHOLD_PERCENT", "0.05")
)
CHRONIC_CONDITION_MIN_REPORTS: int = int(
    os.getenv("CHRONIC_CONDITION_MIN_REPORTS", "2")
)
CHRONIC_CONDITION_MIN_DAYS: int = int(
    os.getenv("CHRONIC_CONDITION_MIN_DAYS", "30")
)

DIET_GENERATION_MODEL: str = os.getenv(
    "DIET_GENERATION_MODEL", "llama-3.3-70b-versatile"
)
DIET_GENERATION_MODEL_FALLBACK: str = os.getenv(
    "DIET_GENERATION_MODEL_FALLBACK", "qwen/qwen3-32b"
)
MAX_DIET_GENERATION_RETRIES: int = int(
    os.getenv("MAX_DIET_GENERATION_RETRIES", "2")
)

if not GROQ_API_KEY:
    import warnings
    warnings.warn("GROQ_API_KEY is not set.", stacklevel=2)
