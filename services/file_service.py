"""File service — framework-agnostic file validation and storage."""

import hashlib
import logging
import uuid
from pathlib import Path

from config.settings import ALLOWED_EXTENSIONS, UPLOAD_DIR, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """Raised when a file fails validation (extension, size, etc.)."""


def validate_file(filename: str, content: bytes) -> str:
    """Validate file extension and size. Returns lowercase extension."""
    if not filename:
        raise FileValidationError("No filename provided.")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise FileValidationError(
            f"File exceeds {MAX_FILE_SIZE_MB} MB limit ({size_mb:.1f} MB)."
        )

    return ext


def save_single_upload(filename: str, content: bytes) -> dict:
    """Validate and save a single file, creating a new session."""
    ext = validate_file(filename, content)

    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    saved_filename = f"report{ext}"
    file_path = session_dir / saved_filename

    try:
        file_path.write_bytes(content)
    except OSError as exc:
        raise FileValidationError(f"Failed to save file: {exc}") from exc

    size_mb = len(content) / (1024 * 1024)
    logger.info("Session %s — saved %s (%.1f MB)", session_id, saved_filename, size_mb)

    return {
        "session_id": session_id,
        "file_path": str(file_path),
    }


def save_document_to_session(
    filename: str,
    content: bytes,
    session_id: str,
    doc_id: str,
) -> dict:
    """Save a file as part of a multi-document session."""
    ext = validate_file(filename, content)
    file_hash = hashlib.sha256(content).hexdigest()

    doc_dir = UPLOAD_DIR / session_id / "documents" / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    saved_filename = f"original{ext}"
    file_path = doc_dir / saved_filename

    try:
        file_path.write_bytes(content)
    except OSError as exc:
        raise FileValidationError(f"Failed to save file: {exc}") from exc

    size_mb = len(content) / (1024 * 1024)
    logger.info(
        "Session %s / Doc %s — saved %s (%.1f MB)",
        session_id, doc_id, filename, size_mb,
    )

    return {
        "file_path": str(file_path),
        "file_hash": file_hash,
        "original_filename": filename,
    }
