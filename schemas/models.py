"""Pydantic response models for the API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    version: str = "0.4.0"


class BMIResult(BaseModel):
    bmi_value: float | None = None
    classification: str | None = None
    category: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    source: str | None = None


class ProcessReportResponse(BaseModel):
    """Single-document response."""

    session_id: str
    patient_information: dict[str, Any] = Field(default_factory=dict)
    tests_index: dict[str, Any] = Field(default_factory=dict)
    tests_by_category: dict[str, Any] = Field(default_factory=dict)
    abnormal_findings: list[dict[str, Any]] = Field(default_factory=list)
    clinical_notes: dict[str, Any] = Field(default_factory=dict)
    bmi: BMIResult | dict[str, Any] | None = None
    processing_time_seconds: float = 0.0


class DocumentSummary(BaseModel):
    doc_id: str | None = None
    original_filename: str | None = None
    status: str = "unknown"
    doc_type: str | None = None
    user_declared_type: str | None = None
    error: str | None = None

    class Config:
        extra = "allow"


class ProcessReportsResponse(BaseModel):
    """Multi-document aggregated response."""

    session_id: str
    documents_processed: int = 0
    documents_failed: int = 0
    documents_skipped_duplicate: int = 0
    patient_information: dict[str, Any] = Field(default_factory=dict)
    aggregated_tests: dict[str, Any] = Field(default_factory=dict)
    aggregated_abnormal_findings: list[dict[str, Any]] = Field(default_factory=list)
    chronic_flags: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    aggregation_status: str = "unknown"
    bmi: BMIResult | dict[str, Any] | None = None
    per_document_results: list[DocumentSummary | dict[str, Any]] = Field(
        default_factory=list,
    )
    processing_time_seconds: float = 0.0


class SafetyCheckResult(BaseModel):
    safe: bool = True
    warning_count: int = 0
    critical_warnings: int = 0
    warnings: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        extra = "allow"


class DietGenerationMetadata(BaseModel):
    skipped: bool = False
    reason: str | None = None
    error: str | None = None
    structural_warnings: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


class DietPlanResponse(ProcessReportsResponse):
    """Full pipeline response including diet plan."""

    diet_plan: dict[str, Any] | None = None
    safety_checks: SafetyCheckResult | dict[str, Any] | None = None
    diet_generation_metadata: DietGenerationMetadata | dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    detail: str


class TaskSubmittedResponse(BaseModel):
    """Returned when a background task is accepted."""

    task_id: str
    status: str = "queued"
    message: str = "Task accepted. Poll GET /api/v1/tasks/{task_id} for progress."


class TaskStatusResponse(BaseModel):
    """Returned by the task-polling endpoint."""

    task_id: str
    task_type: str
    status: str  # queued | processing | complete | failed
    progress: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
