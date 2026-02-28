"""Reports router — single and multi-document endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.dependencies import require_api_key
from schemas.models import ProcessReportResponse, ProcessReportsResponse
from services.file_service import FileValidationError
from services.report_service import PipelineError, process_multiple_reports, process_single_report

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Reports"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/process-report", response_model=ProcessReportResponse)
async def process_report(file: UploadFile = File(...)):
    """Process a single medical report and return structured extraction."""
    logger.info("Received file: %s (%s)", file.filename, file.content_type)

    content = await file.read()

    try:
        result = await asyncio.to_thread(
            process_single_report, file.filename or "upload", content,
        )
    except PipelineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    result.pop("raw_ocr_text", None)
    result.pop("structured_json", None)
    return result


@router.post("/process-reports", response_model=ProcessReportsResponse)
async def process_reports(files: list[UploadFile] = File(...)):
    """Process multiple medical reports and return an aggregated health state."""
    logger.info(
        "Multi-doc upload: %d file(s) — %s",
        len(files),
        [f.filename for f in files],
    )

    raw_files: list[tuple[str, bytes]] = []
    for f in files:
        raw_files.append((f.filename or "upload", await f.read()))

    try:
        result = await process_multiple_reports(raw_files)
    except PipelineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    result.pop("_successful_docs", None)
    return result
