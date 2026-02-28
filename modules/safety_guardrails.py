"""Safety guardrails for generated diet plans."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def _check_caloric_floor(
    plan: dict,
    patient_info: dict,
    bmi: dict | None,
) -> list[dict]:
    """Check that total calories meet minimum safe thresholds."""
    warnings: list[dict] = []

    age = patient_info.get("age_years")
    bmi_val = bmi.get("bmi_value") if bmi else None

    if age is not None and age < 18:
        min_kcal = 1400
        reason = "pediatric patient"
    elif age is not None and age >= 65:
        min_kcal = 1200
        reason = "elderly patient (≥65)"
    elif bmi_val is not None and bmi_val < 18.5:
        min_kcal = 1500
        reason = "underweight patient (BMI < 18.5)"
    else:
        min_kcal = 1000
        reason = "general safety floor"

    # Try to extract caloric target from the plan
    guidelines = plan.get("dietary_guidelines", {})
    caloric_target = guidelines.get("caloric_target", {})
    range_str = caloric_target.get("range_kcal", "")

    # Parse first number from range string
    numbers = re.findall(r"\d+", str(range_str))
    if numbers:
        lowest_kcal = int(numbers[0])
        if lowest_kcal < min_kcal:
            warnings.append({
                "type": "caloric_floor_violation",
                "severity": "critical",
                "message": (
                    f"Plan recommends {lowest_kcal} kcal/day, but minimum "
                    f"safe intake for {reason} is {min_kcal} kcal/day."
                ),
                "recommendation": (
                    "Increase caloric target. Consult a physician before "
                    "implementing any low-calorie diet for this patient."
                ),
            })

    return warnings


def _check_macronutrient_extremes(plan: dict) -> list[dict]:
    """Flag dangerously low or high macronutrient ratios."""
    warnings: list[dict] = []
    guidelines = plan.get("dietary_guidelines", {})
    macro = guidelines.get("macronutrient_split", {})

    protein_pct = macro.get("protein_percent")
    carbs_pct = macro.get("carbs_percent")
    fat_pct = macro.get("fat_percent")

    if protein_pct is not None:
        try:
            p = float(protein_pct)
            if p < 10:
                warnings.append({
                    "type": "extreme_protein_restriction",
                    "severity": "high",
                    "message": f"Protein at {p}% is dangerously low for most patients.",
                    "recommendation": "Verify if CKD stage 4-5 justifies this level.",
                })
            elif p > 40:
                warnings.append({
                    "type": "excessive_protein",
                    "severity": "moderate",
                    "message": f"Protein at {p}% may stress kidneys in susceptible patients.",
                    "recommendation": "Verify renal function supports this protein load.",
                })
        except (ValueError, TypeError):
            pass

    if carbs_pct is not None:
        try:
            c = float(carbs_pct)
            if c < 10:
                warnings.append({
                    "type": "extreme_carb_restriction",
                    "severity": "moderate",
                    "message": (
                        f"Carbohydrates at {c}% is an extreme restriction. "
                        "This level can cause ketoacidosis in diabetics on insulin."
                    ),
                    "recommendation": "Ensure this is medically supervised.",
                })
        except (ValueError, TypeError):
            pass

    if fat_pct is not None:
        try:
            f = float(fat_pct)
            if f < 15:
                warnings.append({
                    "type": "extreme_fat_restriction",
                    "severity": "moderate",
                    "message": f"Fat at {f}% may impair absorption of fat-soluble vitamins.",
                    "recommendation": "Consider vitamin A, D, E, K supplementation.",
                })
        except (ValueError, TypeError):
            pass

    return warnings


_MEDICATION_FOOD_INTERACTIONS: list[dict] = [
    {
        "drug_keywords": ["warfarin", "coumadin"],
        "food_keywords": ["vitamin k", "leafy green", "spinach", "kale", "broccoli"],
        "interaction": (
            "Warfarin requires CONSISTENT vitamin K intake. The plan should "
            "NOT tell the patient to increase OR decrease leafy greens — "
            "only to keep intake consistent."
        ),
        "check_type": "consistency",
    },
    {
        "drug_keywords": ["metformin"],
        "food_keywords": ["alcohol", "beer", "wine", "spirits"],
        "interaction": (
            "Metformin + alcohol increases lactic acidosis risk. "
            "The plan must recommend limiting alcohol."
        ),
        "check_type": "restrict",
    },
    {
        "drug_keywords": ["statin", "atorvastatin", "rosuvastatin", "simvastatin"],
        "food_keywords": ["grapefruit"],
        "interaction": (
            "Grapefruit inhibits CYP3A4, increasing statin blood levels "
            "and risk of rhabdomyolysis. Must avoid grapefruit."
        ),
        "check_type": "restrict",
    },
    {
        "drug_keywords": ["lithium"],
        "food_keywords": ["sodium", "salt"],
        "interaction": (
            "Lithium levels are sodium-dependent. Sudden sodium changes "
            "can cause toxicity or sub-therapeutic levels. "
            "Sodium intake must remain CONSISTENT."
        ),
        "check_type": "consistency",
    },
    {
        "drug_keywords": ["ace inhibitor", "lisinopril", "enalapril", "ramipril"],
        "food_keywords": ["potassium", "banana", "orange", "potato", "tomato"],
        "interaction": (
            "ACE inhibitors raise potassium levels. Adding high-potassium "
            "foods without monitoring can cause hyperkalemia."
        ),
        "check_type": "restrict",
    },
    {
        "drug_keywords": ["maoi", "phenelzine", "tranylcypromine"],
        "food_keywords": ["tyramine", "aged cheese", "fermented", "soy sauce", "wine"],
        "interaction": (
            "MAOIs + tyramine-rich foods can cause hypertensive crisis. "
            "Strict avoidance is required."
        ),
        "check_type": "restrict",
    },
]


def _check_medication_interactions(
    plan: dict,
    medications_text: str,
) -> list[dict]:
    """
    Cross-check the diet plan against known drug–food interactions.

    This is deterministic (not LLM-based) and catches interactions
    even if the LLM forgot to account for them.
    """
    warnings: list[dict] = []

    if not medications_text or medications_text.startswith("No prescription"):
        return warnings

    meds_lower = medications_text.lower()
    plan_str = str(plan).lower()

    for interaction in _MEDICATION_FOOD_INTERACTIONS:
        # Check if any drug keyword is in the medications
        drug_match = any(kw in meds_lower for kw in interaction["drug_keywords"])
        if not drug_match:
            continue

        # Check if the plan mentions the conflicting food
        food_mentioned = any(kw in plan_str for kw in interaction["food_keywords"])

        if interaction["check_type"] == "restrict" and food_mentioned:
            # Plan recommends a food that should be restricted
            warnings.append({
                "type": "medication_diet_interaction",
                "severity": "high",
                "drugs": [kw for kw in interaction["drug_keywords"] if kw in meds_lower],
                "message": interaction["interaction"],
                "recommendation": "Review the meal plan for these specific foods.",
            })
        elif interaction["check_type"] == "consistency":
            # These are informational — the plan should maintain consistency
            warnings.append({
                "type": "medication_diet_consistency_required",
                "severity": "moderate",
                "drugs": [kw for kw in interaction["drug_keywords"] if kw in meds_lower],
                "message": interaction["interaction"],
                "recommendation": (
                    "Ensure the meal plan maintains CONSISTENT intake of "
                    "these foods across all 7 days — not elimination or increase."
                ),
            })

    return warnings


def _check_disclaimer(plan: dict) -> list[dict]:
    """Ensure the plan contains a medical disclaimer."""
    warnings: list[dict] = []

    disclaimer = plan.get("disclaimer", "")
    if not disclaimer or len(disclaimer) < 20:
        warnings.append({
            "type": "missing_disclaimer",
            "severity": "critical",
            "message": "Diet plan is missing the medical disclaimer.",
            "recommendation": "A disclaimer has been forcibly injected.",
        })
        plan["disclaimer"] = (
            "This diet plan is AI-generated based on lab data and should not "
            "replace professional medical advice. Consult a registered "
            "dietitian or physician before making dietary changes."
        )

    return warnings


def _check_data_confidence(
    plan: dict,
    aggregated_state: dict,
) -> list[dict]:
    """
    Assess and warn about data quality issues that reduce confidence
    in the diet plan.
    """
    warnings: list[dict] = []

    # Few test results
    tests = aggregated_state.get("aggregated_tests", {})
    if len(tests) < 3:
        warnings.append({
            "type": "insufficient_lab_data",
            "severity": "moderate",
            "message": (
                f"Only {len(tests)} test(s) available. Diet plan accuracy "
                "is limited with sparse lab data."
            ),
            "recommendation": "Upload additional lab reports for a more comprehensive plan.",
        })

    # Missing patient demographics
    patient = aggregated_state.get("patient_information", {})
    missing_fields: list[str] = []
    if not patient.get("age_years"):
        missing_fields.append("age")
    if not patient.get("gender"):
        missing_fields.append("gender")
    if not aggregated_state.get("bmi"):
        missing_fields.append("BMI")

    if missing_fields:
        warnings.append({
            "type": "missing_demographics",
            "severity": "moderate",
            "message": (
                f"Missing patient data: {', '.join(missing_fields)}. "
                "Diet recommendations may be less personalized."
            ),
            "recommendation": "Provide patient demographics for better accuracy.",
        })

    # Unresolved conflicts
    conflicts = aggregated_state.get("conflicts", [])
    if conflicts:
        warnings.append({
            "type": "unresolved_conflicts_present",
            "severity": "moderate",
            "message": (
                f"{len(conflicts)} data conflict(s) exist. The LLM used "
                "potentially unreliable values for diet generation."
            ),
            "recommendation": "Re-test conflicting values before following the plan.",
        })

    return warnings


def run_safety_checks(
    diet_plan: dict,
    aggregated_state: dict,
    medications_text: str = "",
) -> dict:
    """Run all safety checks on a generated diet plan."""
    all_warnings: list[dict] = []

    patient_info = aggregated_state.get("patient_information", {})
    bmi = aggregated_state.get("bmi")

    all_warnings.extend(_check_caloric_floor(diet_plan, patient_info, bmi))
    all_warnings.extend(_check_macronutrient_extremes(diet_plan))
    all_warnings.extend(
        _check_medication_interactions(diet_plan, medications_text)
    )
    all_warnings.extend(_check_disclaimer(diet_plan))
    all_warnings.extend(_check_data_confidence(diet_plan, aggregated_state))

    critical_count = sum(
        1 for w in all_warnings if w.get("severity") == "critical"
    )

    result = {
        "safe": critical_count == 0,
        "warnings": all_warnings,
        "warning_count": len(all_warnings),
        "critical_warnings": critical_count,
    }

    if all_warnings:
        logger.warning(
            "Safety guardrails raised %d warning(s) (%d critical)",
            len(all_warnings), critical_count,
        )
    else:
        logger.info("Safety guardrails: all checks passed")

    return result
