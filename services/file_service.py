"""File service — framework-agnostic file validation, storage, and cleanup."""

import hashlib
import logging
import shutil
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


def validate_and_hash(filename: str, content: bytes) -> tuple[str, str]:
    """Validate a file and return ``(ext, sha256_hex)`` — no disk I/O."""
    ext = validate_file(filename, content)
    file_hash = hashlib.sha256(content).hexdigest()
    return ext, file_hash


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


# --- Cleanup utilities -------------------------------------------------------

def cleanup_session_files(session_id: str) -> bool:
    """Remove all uploaded files for a session from disk.

    Call this after processing is complete so that no PHI/PII
    remains on the file system longer than necessary.

    Returns ``True`` if files were deleted, ``False`` if the
    directory did not exist.
    """
    session_dir = UPLOAD_DIR / session_id
    if not session_dir.exists():
        return False

    try:
        shutil.rmtree(session_dir)
        logger.info("Cleaned up session files: %s", session_id)
        return True
    except OSError as exc:
        logger.error("Failed to clean up session %s: %s", session_id, exc)
        return False


def cleanup_document_files(session_id: str, doc_id: str) -> bool:
    """Remove uploaded files for a single document."""
    doc_dir = UPLOAD_DIR / session_id / "documents" / doc_id
    if not doc_dir.exists():
        return False

    try:
        shutil.rmtree(doc_dir)
        logger.info("Cleaned up doc files: %s/%s", session_id, doc_id)
        return True
    except OSError as exc:
        logger.error(
            "Failed to clean up doc %s/%s: %s", session_id, doc_id, exc,
        )
        return False


def cleanup_stale_sessions(max_age_hours: int = 1) -> int:
    """Remove session directories older than *max_age_hours*.

    Intended to be called periodically (e.g. via a background task)
    to purge any files that survived individual session cleanup.
    Returns the number of directories removed.
    """
    import time

    if not UPLOAD_DIR.exists():
        return 0

    cutoff = time.time() - max_age_hours * 3600
    removed = 0

    for child in UPLOAD_DIR.iterdir():
        if not child.is_dir():
            continue
        try:
            if child.stat().st_mtime < cutoff:
                shutil.rmtree(child)
                removed += 1
                logger.info("Purged stale session dir: %s", child.name)
        except OSError as exc:
            logger.warning("Could not purge %s: %s", child.name, exc)

    if removed:
        logger.info("Stale session cleanup: removed %d dir(s)", removed)
    return removed
