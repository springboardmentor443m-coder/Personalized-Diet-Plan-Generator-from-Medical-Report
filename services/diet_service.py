"""Diet service — diet plan generation + safety checks."""

import logging
from typing import Any

from modules.diet_prompt_builder import _format_medications
from modules.diet_generator import generate_diet_plan
from modules.safety_guardrails import run_safety_checks

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

    # Build aggregated state for diet generator
    aggregated_state = {
        "aggregated_tests": aggregation_result.get("aggregated_tests", {}),
        "aggregated_abnormal_findings": aggregation_result.get("aggregated_abnormal_findings", []),
        "chronic_flags": aggregation_result.get("chronic_flags", []),
        "conflicts": aggregation_result.get("conflicts", []),
        "aggregation_status": aggregation_result.get("aggregation_status", ""),
        "patient_information": aggregation_result.get("patient_information", {}),
        "bmi": aggregation_result.get("bmi"),
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

    logger.info(
        "Diet generated: safe=%s, warnings=%d, critical=%d",
        safety_result["safe"],
        safety_result["warning_count"],
        safety_result["critical_warnings"],
    )

    return {
        "diet_plan": diet_plan,
        "safety_checks": safety_result,
        "diet_generation_metadata": {
            **gen_metadata,
            "structural_warnings": structural_warnings,
        },
    }
