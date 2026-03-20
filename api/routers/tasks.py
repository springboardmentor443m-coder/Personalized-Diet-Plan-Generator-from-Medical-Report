"""Tasks router — background task submission and polling."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from api.dependencies import require_api_key
from schemas.models import TaskSubmittedResponse, TaskStatusResponse
from services import database as db
from services.diet_service import generate_diet_from_results
from services.report_service import process_multiple_reports

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Tasks"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/tasks/process-reports", response_model=TaskSubmittedResponse, status_code=202)
async def submit_process_reports(files: list[UploadFile] = File(...)):
    """Submit multi-document processing as a background task."""
    raw_files: list[tuple[str, bytes]] = []
    for f in files:
        raw_files.append((f.filename or "upload", await f.read()))

    task_id = db.create_task(
        task_type="process_reports",
        input_data={"filenames": [fn for fn, _ in raw_files]},
    )
    asyncio.get_event_loop().create_task(_run_process_reports(task_id, raw_files))
    return TaskSubmittedResponse(task_id=task_id)


async def _run_process_reports(task_id: str, raw_files: list[tuple[str, bytes]]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db.update_task(task_id, status="processing", started_at=now, progress="Starting pipeline")

    try:
        result = await process_multiple_reports(raw_files)
        result.pop("_successful_docs", None)
        db.update_task(
            task_id,
            status="complete",
            completed_at=datetime.now(timezone.utc).isoformat(),
            result_json=result,
            session_id=result.get("session_id"),
            progress="Done",
        )
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        db.update_task(
            task_id,
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
            progress="Failed",
        )


@router.post("/tasks/generate-diet-plan", response_model=TaskSubmittedResponse, status_code=202)
async def submit_generate_diet(
    files: list[UploadFile] = File(...),
    dietary_preferences: str | None = Form(None),
):
    """Submit full pipeline + diet plan generation as a background task."""
    raw_files: list[tuple[str, bytes]] = []
    for f in files:
        raw_files.append((f.filename or "upload", await f.read()))

    prefs: dict = {}
    if dietary_preferences:
        try:
            prefs = json.loads(dietary_preferences)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="dietary_preferences must be valid JSON")

    task_id = db.create_task(
        task_type="generate_diet",
        input_data={
            "filenames": [fn for fn, _ in raw_files],
            "dietary_preferences": prefs if prefs else None,
        },
    )
    asyncio.get_event_loop().create_task(_run_diet_task(task_id, raw_files, prefs))
    return TaskSubmittedResponse(task_id=task_id)


async def _run_diet_task(
    task_id: str,
    raw_files: list[tuple[str, bytes]],
    dietary_preferences: dict | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db.update_task(task_id, status="processing", started_at=now, progress="Processing reports")

    try:
        multi_result = await process_multiple_reports(raw_files)
        db.update_task(task_id, progress="Generating diet plan")

        diet_output = await asyncio.to_thread(
            generate_diet_from_results,
            multi_result,
            None,
            dietary_preferences or {},
        )
        multi_result.pop("_successful_docs", None)
        multi_result.update(diet_output)

        session_id = multi_result.get("session_id")
        if session_id:
            db.save_diet_result(
                session_id,
                diet_plan=diet_output.get("diet_plan"),
                safety=diet_output.get("safety_checks"),
                diet_meta=diet_output.get("diet_generation_metadata"),
            )

        db.update_task(
            task_id,
            status="complete",
            completed_at=datetime.now(timezone.utc).isoformat(),
            result_json=multi_result,
            session_id=session_id,
            progress="Done",
        )
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        db.update_task(
            task_id,
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
            progress="Failed",
        )


@router.post("/tasks/regenerate-diet-plan", response_model=TaskSubmittedResponse, status_code=202)
async def submit_regenerate_diet(payload: dict[str, Any] = Body(...)):
    """Regenerate diet plan from existing aggregated result + new preferences."""
    aggregation_result = payload.get("aggregation_result")
    if not isinstance(aggregation_result, dict):
        raise HTTPException(status_code=400, detail="aggregation_result must be an object")

    prefs = payload.get("dietary_preferences") or {}
    if not isinstance(prefs, dict):
        raise HTTPException(status_code=400, detail="dietary_preferences must be an object")

    task_id = db.create_task(
        task_type="regenerate_diet",
        input_data={
            "session_id": aggregation_result.get("session_id"),
            "has_preferences": bool(prefs),
        },
    )
    asyncio.get_event_loop().create_task(_run_regenerate_diet_task(task_id, aggregation_result, prefs))
    return TaskSubmittedResponse(task_id=task_id)


async def _run_regenerate_diet_task(
    task_id: str,
    aggregation_result: dict[str, Any],
    dietary_preferences: dict[str, Any] | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db.update_task(task_id, status="processing", started_at=now, progress="Regenerating diet plan")

    try:
        base_result = dict(aggregation_result)
        # Drop prior generated artifacts to avoid stale payload collisions.
        for key in ("diet_plan", "safety_checks", "diet_generation_metadata", "output_validation"):
            base_result.pop(key, None)

        diet_output = await asyncio.to_thread(
            generate_diet_from_results,
            base_result,
            None,
            dietary_preferences or {},
        )

        base_result.update(diet_output)

        session_id = base_result.get("session_id")
        if session_id:
            db.save_diet_result(
                session_id,
                diet_plan=diet_output.get("diet_plan"),
                safety=diet_output.get("safety_checks"),
                diet_meta=diet_output.get("diet_generation_metadata"),
            )

        db.update_task(
            task_id,
            status="complete",
            completed_at=datetime.now(timezone.utc).isoformat(),
            result_json=base_result,
            session_id=session_id,
            progress="Done",
        )
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        db.update_task(
            task_id,
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
            progress="Failed",
        )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Poll the status of a background task."""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return TaskStatusResponse(
        task_id=task["id"],
        task_type=task["task_type"],
        status=task["status"],
        progress=task.get("progress"),
        result=task.get("result_json") if task["status"] == "complete" else None,
        error=task.get("error"),
        created_at=task.get("created_at"),
        started_at=task.get("started_at"),
        completed_at=task.get("completed_at"),
    )
