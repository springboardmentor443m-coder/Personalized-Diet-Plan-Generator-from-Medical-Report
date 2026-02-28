"""Report service — single and multi-document processing pipeline.

Files are processed in-memory wherever possible.  Disk is only used
when a database audit-trail record is needed, and those temporary
files are automatically removed once processing completes.
"""

import asyncio
import hashlib
import logging
import time
import uuid
from pathlib import Path

from config.settings import (
    INTER_DOCUMENT_DELAY_SECONDS,
    MAX_DOCUMENTS_PER_SESSION,
    UPLOAD_DIR,
)
from modules.pdf_to_image import convert_bytes_to_images
from modules.ocr import run_ocr
from modules.structured_extraction import extract_structured_data
from modules.bmi import calculate_bmi
from modules.document_classifier import classify_document
from modules.health_state_aggregator import aggregate_health_state
from services import database as db
from services.file_service import (
    validate_and_hash,
    save_document_to_session,
    cleanup_session_files,
    FileValidationError,
)

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def _process_document_core_bytes(content: bytes, ext: str) -> dict:
    """Run image-conversion → OCR → structured extraction → BMI entirely in memory."""
    images = convert_bytes_to_images(content, ext)
    logger.info("Produced %d image(s)", len(images))

    ocr_text = run_ocr(images)
    logger.info("OCR returned %d characters", len(ocr_text))

    structured = extract_structured_data(ocr_text)
    bmi_result = calculate_bmi(structured)

    return {
        "patient_information": structured.get("patient_information", {}),
        "tests_index": structured.get("tests_index", {}),
        "tests_by_category": structured.get("tests_by_category", {}),
        "abnormal_findings": structured.get("abnormal_findings", []),
        "clinical_notes": structured.get("clinical_notes", {}),
        "bmi": bmi_result,
        "raw_ocr_text": ocr_text,
        "structured_json": structured,
    }


def process_single_report(filename: str, content: bytes) -> dict:
    """End-to-end single-file pipeline (fully in-memory — nothing persisted to disk)."""
    pipeline_start = time.time()

    try:
        ext, _hash = validate_and_hash(filename, content)
    except FileValidationError as exc:
        raise PipelineError(str(exc), status_code=400) from exc

    session_id = str(uuid.uuid4())
    logger.info("Session %s — processing %s in-memory", session_id, filename)

    try:
        result = _process_document_core_bytes(content, ext)
    except ValueError as exc:
        raise PipelineError(str(exc), status_code=422) from exc
    except RuntimeError as exc:
        raise PipelineError(str(exc), status_code=502) from exc

    elapsed = round(time.time() - pipeline_start, 2)

    output = {
        "session_id": session_id,
        **result,
        "processing_time_seconds": elapsed,
    }
    logger.info("Pipeline complete for session %s (%.2fs)", session_id, elapsed)
    return output


async def process_multiple_reports(
    files: list[tuple[str, bytes]],
    *,
    user_declared_types: list[str] | None = None,
) -> dict:
    """Process multiple documents sequentially within one session."""
    if len(files) > MAX_DOCUMENTS_PER_SESSION:
        raise PipelineError(
            f"Maximum {MAX_DOCUMENTS_PER_SESSION} documents per session. "
            f"Received {len(files)}.",
            status_code=400,
        )

    pipeline_start = time.time()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    session_id = db.create_session()
    logger.info("Multi-doc session %s — %d file(s)", session_id, len(files))

    doc_results: list[dict] = []
    seen_hashes: set[str] = set()
    skipped_duplicates = 0

    for idx, (filename, content) in enumerate(files):
        doc_id = str(uuid.uuid4())
        doc_start = time.time()

        user_type = (
            user_declared_types[idx]
            if user_declared_types and idx < len(user_declared_types)
            else None
        )

        # Register in session
        db.register_document(
            session_id, doc_id, filename or f"document_{idx + 1}",
        )

        # Validate + hash (in-memory — no disk write yet)
        try:
            ext, file_hash = validate_and_hash(filename, content)
        except FileValidationError as exc:
            logger.error("Doc %d validation failed: %s", idx + 1, exc)
            db.update_document(
                doc_id, status="failed", error=str(exc),
            )
            doc_results.append({
                "doc_id": doc_id,
                "original_filename": filename,
                "status": "failed",
                "error": str(exc),
                "user_declared_type": user_type,
            })
            continue

        # SHA-256 de-duplication
        if file_hash in seen_hashes:
            logger.info("Skipping duplicate: %s (hash=%s…)", filename, file_hash[:12])
            skipped_duplicates += 1
            db.update_document(
                doc_id, status="skipped_duplicate", file_hash=file_hash,
            )
            continue
        seen_hashes.add(file_hash)

        # Process entirely in-memory (no file saved to disk)
        try:
            result = await asyncio.to_thread(
                _process_document_core_bytes, content, ext,
            )
            result["status"] = "processed"
            result["doc_id"] = doc_id
            result["original_filename"] = filename
            result["user_declared_type"] = user_type

            # Classify
            doc_type = classify_document(
                result.get("structured_json", {}),
                result.get("raw_ocr_text", ""),
            )
            result["doc_type"] = doc_type

            doc_results.append(result)

            db.update_document(
                doc_id,
                status="processed",
                doc_type=doc_type,
                report_datetime=result.get("patient_information", {}).get("report_datetime"),
                processing_time=round(time.time() - doc_start, 2),
                file_hash=file_hash,
            )
            db.save_document_result(doc_id, result)

            logger.info(
                "Doc %d/%d processed in-memory (%s, type=%s, %.1fs)",
                idx + 1, len(files), filename, doc_type,
                time.time() - doc_start,
            )

        except Exception as exc:
            logger.error("Doc %d (%s) failed: %s", idx + 1, filename, exc)
            db.update_document(
                doc_id,
                status="failed", error=str(exc),
                processing_time=round(time.time() - doc_start, 2),
                file_hash=file_hash,
            )
            doc_results.append({
                "doc_id": doc_id,
                "original_filename": filename,
                "status": "failed",
                "error": str(exc),
                "user_declared_type": user_type,
            })

        # Rate-limit delay
        if idx < len(files) - 1:
            logger.info(
                "Rate-limit delay: %.1fs before next document",
                INTER_DOCUMENT_DELAY_SECONDS,
            )
            await asyncio.sleep(INTER_DOCUMENT_DELAY_SECONDS)

    # Aggregation
    successful = [r for r in doc_results if r.get("status") == "processed"]

    aggregated: dict = {}
    if successful:
        aggregated = aggregate_health_state(successful)
        db.update_session(
            session_id,
            aggregation_status=aggregated.get("aggregation_status", "complete"),
        )
        db.save_session_result(session_id, aggregated)
    else:
        db.update_session(session_id, aggregation_status="failed")

    # Build response
    elapsed = round(time.time() - pipeline_start, 2)

    per_doc_summary = []
    for r in doc_results:
        summary = {k: v for k, v in r.items() if k not in ("raw_ocr_text", "structured_json")}
        per_doc_summary.append(summary)

    output = {
        "session_id": session_id,
        "documents_processed": len(successful),
        "documents_failed": sum(1 for r in doc_results if r.get("status") == "failed"),
        "documents_skipped_duplicate": skipped_duplicates,
        "patient_information": aggregated.get("patient_information", {}),
        "aggregated_tests": aggregated.get("aggregated_tests", {}),
        "aggregated_abnormal_findings": aggregated.get("aggregated_abnormal_findings", []),
        "chronic_flags": aggregated.get("chronic_flags", []),
        "conflicts": aggregated.get("conflicts", []),
        "aggregation_status": aggregated.get("aggregation_status", "failed"),
        "bmi": aggregated.get("bmi"),
        "per_document_results": per_doc_summary,
        "processing_time_seconds": elapsed,
        "_successful_docs": successful,
    }

    logger.info(
        "Multi-doc pipeline complete: session=%s, processed=%d, failed=%d, "
        "dupes=%d, conflicts=%d, chronic=%d (%.2fs)",
        session_id, len(successful), output["documents_failed"],
        skipped_duplicates, len(output["conflicts"]),
        len(output["chronic_flags"]), elapsed,
    )
    return output
