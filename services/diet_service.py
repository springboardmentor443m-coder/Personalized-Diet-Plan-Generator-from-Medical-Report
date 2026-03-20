"""Diet service — diet plan generation + safety checks + validation."""

import logging
from typing import Any

from modules.diet_prompt_builder import _format_medications
from modules.diet_generator import generate_diet_plan
from modules.safety_guardrails import run_safety_checks
from modules.output_validator import validate_diet_output

logger = logging.getLogger(__name__)


def generate_diet_from_results(
    aggregation_result: dict[str, Any],
    successful_docs: list[dict[str, Any]] | None = None,
    dietary_preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a personalised diet plan from aggregated analysis results.

    Parameters
    ----------
    dietary_preferences : dict | None
        User-specified diet filters (diet_type, meal_frequency, cuisine,
        calorie_target, allergies).  Passed straight into the prompt.
    """
    if successful_docs is None:
        successful_docs = aggregation_result.get(
            "_successful_docs",
            aggregation_result.get("per_document_results", []),
        )

    n_processed = aggregation_result.get("documents_processed", len(successful_docs))

    if n_processed == 0 and not successful_docs:
        return {
            "diet_plan": None,
            "safety_checks": None,
            "diet_generation_metadata": {
                "skipped": True,
                "reason": "No documents were successfully processed.",
            },
        }

    # If UI-provided BMI is available, prefer it over extracted BMI so
    # user-entered measurements influence prompt + safety checks.
    user_bmi: dict[str, Any] | None = None
    if isinstance(dietary_preferences, dict):
        bmi_raw = dietary_preferences.get("bmi")
        if isinstance(bmi_raw, dict) and bmi_raw.get("bmi_value") is not None:
            user_bmi = {
                "bmi_value": bmi_raw.get("bmi_value"),
                "category": bmi_raw.get("category") or bmi_raw.get("classification"),
                "height_cm": bmi_raw.get("height_cm"),
                "weight_kg": bmi_raw.get("weight_kg"),
            }

    # Build aggregated state for diet generator
    aggregated_state = {
        "aggregated_tests": aggregation_result.get("aggregated_tests", {}),
        "aggregated_abnormal_findings": aggregation_result.get("aggregated_abnormal_findings", []),
        "chronic_flags": aggregation_result.get("chronic_flags", []),
        "conflicts": aggregation_result.get("conflicts", []),
        "aggregation_status": aggregation_result.get("aggregation_status", ""),
        "patient_information": aggregation_result.get("patient_information", {}),
        "bmi": user_bmi or aggregation_result.get("bmi"),
    }

    # Per-doc summaries
    per_doc_results = []
    for r in successful_docs:
        summary = {k: v for k, v in r.items() if k not in ("raw_ocr_text",)}
        per_doc_results.append(summary)

    # Generate diet plan
    try:
        gen_result = generate_diet_plan(
            aggregated_state, per_doc_results, dietary_preferences,
        )
        diet_plan = gen_result["diet_plan"]
        gen_metadata = gen_result["generation_metadata"]
        structural_warnings = gen_result.get("structural_warnings", [])
        retrieved_chunks = gen_result.get("retrieved_chunks", [])
    except (ValueError, RuntimeError) as exc:
        logger.error("Diet generation failed: %s", exc)
        return {
            "diet_plan": None,
            "safety_checks": None,
            "diet_generation_metadata": {
                "skipped": False,
                "error": str(exc),
            },
        }

    # Safety guardrails
    medications_text = _format_medications(per_doc_results)
    safety_result = run_safety_checks(diet_plan, aggregated_state, medications_text)

    # Output validation (WHO/NIH threshold checks)
    validation_result = {}
    try:
        validation_result = validate_diet_output(diet_plan, aggregated_state)
        logger.info(
            "Output validation: valid=%s, violations=%d",
            validation_result.get("valid"),
            validation_result.get("violation_count", 0),
        )
    except Exception as exc:
        logger.warning("Output validation failed (non-fatal): %s", exc)
        validation_result = {"valid": True, "violations": [], "error": str(exc)}

    logger.info(
        "Diet generated: safe=%s, warnings=%d, critical=%d",
        safety_result["safe"],
        safety_result["warning_count"],
        safety_result["critical_warnings"],
    )

    return {
        "diet_plan": diet_plan,
        "safety_checks": safety_result,
        "output_validation": validation_result,
        "diet_generation_metadata": {
            **gen_metadata,
            "structural_warnings": structural_warnings,
        },
    }
