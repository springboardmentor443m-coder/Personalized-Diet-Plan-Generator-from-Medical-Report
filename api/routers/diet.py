"""Diet router — full pipeline + diet plan generation."""

import asyncio
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.dependencies import require_api_key
from schemas.models import DietPlanResponse
from services.diet_service import generate_diet_from_results
from services.report_service import PipelineError, process_multiple_reports

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Diet"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/generate-diet-plan", response_model=DietPlanResponse)
async def generate_diet(files: list[UploadFile] = File(...)):
    """Process medical documents and generate a personalised diet plan."""
    logger.info(
        "Diet plan request: %d file(s) — %s",
        len(files),
        [f.filename for f in files],
    )

    raw_files: list[tuple[str, bytes]] = []
    for f in files:
        raw_files.append((f.filename or "upload", await f.read()))

    try:
        multi_result = await process_multiple_reports(raw_files)
    except PipelineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    diet_output = await asyncio.to_thread(generate_diet_from_results, multi_result)

    multi_result.pop("_successful_docs", None)
    multi_result.update(diet_output)
    return multi_result
