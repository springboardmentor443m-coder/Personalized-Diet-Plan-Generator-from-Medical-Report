"""Build system and user prompts for LLM-based diet plan generation."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DIET_SYSTEM_PROMPT = """\
You are a clinical nutrition AI assistant.
You have been trained on evidence-based medical nutrition therapy guidelines.

CRITICAL RULES:
1. You are NOT a doctor. Every recommendation MUST include the disclaimer:
   "Consult a registered dietitian or physician before making dietary changes."
2. NEVER output a fixed diet template. Every recommendation must be personalized
   to the SPECIFIC patient data provided.
3. NEVER map a single lab value to a dietary restriction in isolation.
   Always consider the FULL clinical picture: comorbidities, medications,
   trends, severity, age, BMI, and interactions.
4. If two conditions create CONFLICTING dietary needs (e.g., diabetes + CKD
   require opposing protein guidance), you MUST:
   a. Explicitly acknowledge the conflict
   b. Explain both sides
   c. Recommend the safer conservative option
   d. Flag it for physician review
5. Use GRADED language:
   - "Consider reducing..." (mild abnormality, improving trend)
   - "It is important to limit..." (moderate, stable/worsening)
   - "Urgent dietary modification needed..." (critical, worsening rapidly)
6. For each dietary recommendation, cite the specific lab value(s) that
   drove the recommendation.
7. If data is insufficient to make a safe recommendation for a category,
   say "Insufficient data" rather than guessing.
8. Account for medication–diet interactions:
   - Warfarin → consistent vitamin K intake (don't restrict/increase)
   - Metformin → may need B12 monitoring
   - Statins → grapefruit interaction
   - ACE inhibitors → potassium monitoring
   - Lithium → sodium consistency
9. NEVER recommend extreme caloric restriction for elderly (≥65) or
   underweight patients (BMI < 18.5) regardless of other lab values.
10. When trends show IMPROVEMENT, note specifically that the current dietary
    approach may be working and suggest maintaining rather than intensifying.
"""

DIET_USER_PROMPT_TEMPLATE = """\
Based on the complete clinical profile below, generate a personalized
7-day diet plan with meal-by-meal recommendations.

═══════════════════════════════════════
PATIENT PROFILE
═══════════════════════════════════════
{patient_profile}

═══════════════════════════════════════
CURRENT LAB RESULTS (with trends)
═══════════════════════════════════════
{lab_results}

═══════════════════════════════════════
ABNORMAL FINDINGS (sorted by severity)
═══════════════════════════════════════
{abnormal_findings}

═══════════════════════════════════════
CHRONIC CONDITIONS (persistent abnormalities)
═══════════════════════════════════════
{chronic_conditions}

═══════════════════════════════════════
ACTIVE MEDICATIONS
═══════════════════════════════════════
{medications}

═══════════════════════════════════════
DIAGNOSES
═══════════════════════════════════════
{diagnoses}

═══════════════════════════════════════
UNRESOLVED DATA CONFLICTS
═══════════════════════════════════════
{conflicts}

═══════════════════════════════════════
RESPONSE FORMAT (STRICT JSON)
═══════════════════════════════════════
Return a JSON object with this exact structure:

{{
  "clinical_reasoning": {{
    "primary_concerns": [
      {{
        "concern": string,
        "severity": "mild" | "moderate" | "severe" | "critical",
        "trend": "improving" | "stable" | "worsening" | null,
        "driving_lab_values": [string],
        "dietary_implication": string
      }}
    ],
    "comorbidity_interactions": [
      {{
        "conditions": [string, string],
        "conflict_type": string,
        "resolution": string,
        "confidence": "high" | "moderate" | "low"
      }}
    ],
    "medication_diet_interactions": [
      {{
        "medication": string,
        "dietary_consideration": string,
        "action": string
      }}
    ]
  }},

  "dietary_guidelines": {{
    "caloric_target": {{
      "range_kcal": string,
      "rationale": string
    }},
    "macronutrient_split": {{
      "protein_percent": number,
      "carbs_percent": number,
      "fat_percent": number,
      "rationale": string
    }},
    "key_nutrients_to_increase": [
      {{
        "nutrient": string,
        "reason": string,
        "food_sources": [string]
      }}
    ],
    "key_nutrients_to_limit": [
      {{
        "nutrient": string,
        "reason": string,
        "max_daily": string | null
      }}
    ],
    "foods_to_avoid": [
      {{
        "food_or_category": string,
        "reason": string,
        "severity": "avoid_completely" | "limit_significantly" | "moderate"
      }}
    ],
    "foods_to_emphasize": [
      {{
        "food_or_category": string,
        "reason": string,
        "frequency": string
      }}
    ]
  }},

  "weekly_meal_plan": {{
    "day_1": {{
      "breakfast": {{ "meal": string, "calories_approx": number, "notes": string }},
      "mid_morning_snack": {{ "meal": string, "calories_approx": number, "notes": string }},
      "lunch": {{ "meal": string, "calories_approx": number, "notes": string }},
      "evening_snack": {{ "meal": string, "calories_approx": number, "notes": string }},
      "dinner": {{ "meal": string, "calories_approx": number, "notes": string }}
    }},
    "day_2": {{ "..." : "same structure" }},
    "day_3": {{ "..." : "same structure" }},
    "day_4": {{ "..." : "same structure" }},
    "day_5": {{ "..." : "same structure" }},
    "day_6": {{ "..." : "same structure" }},
    "day_7": {{ "..." : "same structure" }}
  }},

  "monitoring_recommendations": [
    {{
      "test": string,
      "current_status": string,
      "recheck_in": string,
      "dietary_goal": string
    }}
  ],

  "confidence_assessment": {{
    "overall_confidence": "high" | "moderate" | "low",
    "data_quality_notes": [string],
    "limitations": [string]
  }},

  "disclaimer": "This diet plan is AI-generated based on lab data and should not replace professional medical advice. Consult a registered dietitian or physician before making dietary changes."
}}
"""


def _format_patient_profile(
    patient_info: dict,
    bmi: dict | None,
) -> str:
    """Build a human-readable patient profile string."""
    lines: list[str] = []

    name = patient_info.get("patient_name")
    if name:
        lines.append(f"Name: {name}")

    age = patient_info.get("age_years")
    if age is not None:
        lines.append(f"Age: {age} years")
        if age >= 65:
            lines.append("⚠ ELDERLY PATIENT — avoid aggressive caloric restriction")
        elif age < 18:
            lines.append("⚠ PEDIATRIC PATIENT — growth requirements must be prioritized")

    gender = patient_info.get("gender")
    if gender:
        lines.append(f"Gender: {gender}")

    if bmi:
        bmi_val = bmi.get("bmi_value")
        bmi_cat = bmi.get("category")
        lines.append(f"BMI: {bmi_val} ({bmi_cat})")
        if bmi_val and bmi_val < 18.5:
            lines.append("⚠ UNDERWEIGHT — caloric restriction is contraindicated")

    if not lines:
        lines.append("No patient demographic data available")

    return "\n".join(lines)


def _format_lab_results(aggregated_tests: dict) -> str:
    """Format all lab results with trends and history for the LLM."""
    if not aggregated_tests:
        return "No lab results available"

    lines: list[str] = []

    by_category: dict[str, list[tuple[str, dict]]] = {}
    for key, test in aggregated_tests.items():
        cat = test.get("category", "other")
        by_category.setdefault(cat, []).append((key, test))

    for category, tests in sorted(by_category.items()):
        lines.append(f"\n── {category.upper().replace('_', ' ')} ──")

        for key, test in tests:
            value = test.get("current_value")
            units = test.get("units", "")
            ref = test.get("reference_range", "")
            interp = test.get("current_interpretation", "")
            trend = test.get("trend")
            prev_val = test.get("previous_value")
            prev_interp = test.get("previous_interpretation")
            name = test.get("test_name", key)

            line = f"  {name}: {value} {units}"
            if ref:
                line += f"  (ref: {ref})"
            if interp:
                line += f"  [{interp.upper()}]"
            if trend:
                line += f"  trend: {trend}"
            if prev_val is not None:
                line += f"  (previous: {prev_val}"
                if prev_interp:
                    line += f" [{prev_interp}]"
                line += ")"
            lines.append(line)

            history = test.get("history", [])
            if len(history) > 2:
                lines.append(f"    History ({len(history)} readings):")
                for h in history:
                    date = h.get("date", "unknown date")
                    lines.append(
                        f"      {date}: {h.get('value')} [{h.get('interpretation', '?')}]"
                    )

    return "\n".join(lines)


def _format_abnormal_findings(abnormal: list[dict]) -> str:
    """Format abnormal findings sorted by severity."""
    if not abnormal:
        return "No abnormal findings"

    lines: list[str] = []
    for finding in abnormal:
        key = finding.get("canonical_test_key", "")
        val = finding.get("observed_value", "")
        ref = finding.get("expected_range", "")
        sev = finding.get("severity", "")
        trend = finding.get("trend")

        line = f"  • {key}: {val} (range: {ref}) — {sev.upper()}"
        if trend:
            line += f", trend: {trend}"
        lines.append(line)

    return "\n".join(lines)


def _format_chronic_conditions(chronic_flags: list[dict]) -> str:
    """Format chronic condition flags."""
    if not chronic_flags:
        return "No chronic conditions detected from available reports"

    lines: list[str] = []
    for flag in chronic_flags:
        key = flag.get("test_key", "")
        name = flag.get("test_name", key)
        abnorm = flag.get("abnormality_type", "")
        span = flag.get("span_days", 0)
        count = flag.get("occurrences", 0)
        first = flag.get("first_seen", "")
        last = flag.get("last_seen", "")

        lines.append(
            f"  • {name}: persistently {abnorm} across {count} reports "
            f"over {span} days ({first} → {last})"
        )

    return "\n".join(lines)


def _format_medications(per_doc_results: list[dict]) -> str:
    """Extract medication mentions from prescription-type documents."""
    meds: list[str] = []

    for doc in per_doc_results:
        if doc.get("doc_type") != "prescription":
            continue
        notes = doc.get("clinical_notes", {})
        for section in ["recommendations", "comments", "notes"]:
            entries = notes.get(section, [])
            meds.extend(entries)

    if not meds:
        return "No prescription data available — medication interactions cannot be assessed"

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for m in meds:
        m_lower = m.strip().lower()
        if m_lower and m_lower not in seen:
            seen.add(m_lower)
            unique.append(f"  • {m.strip()}")

    return "\n".join(unique)


def _format_diagnoses(per_doc_results: list[dict]) -> str:
    """Extract diagnoses from discharge/diagnosis-type documents."""
    diagnoses: list[str] = []

    for doc in per_doc_results:
        if doc.get("doc_type") not in ("discharge_summary", "diagnosis"):
            continue
        notes = doc.get("clinical_notes", {})
        for section in ["interpretations", "comments", "notes"]:
            entries = notes.get(section, [])
            diagnoses.extend(entries)

    if not diagnoses:
        return "No diagnosis/discharge data available"

    seen: set[str] = set()
    unique: list[str] = []
    for d in diagnoses:
        d_lower = d.strip().lower()
        if d_lower and d_lower not in seen:
            seen.add(d_lower)
            unique.append(f"  • {d.strip()}")

    return "\n".join(unique)


def _format_conflicts(conflicts: list[dict]) -> str:
    """Format unresolved data conflicts the LLM should be aware of."""
    if not conflicts:
        return "No data conflicts"

    lines: list[str] = []
    for c in conflicts:
        key = c.get("test_key", "")
        date = c.get("date", "")
        reason = c.get("reason", "")
        vals = c.get("values", [])
        val_str = ", ".join(str(v.get("value")) for v in vals)
        lines.append(
            f"  • {key} on {date}: conflicting values ({val_str}) — {reason}"
        )
    lines.append(
        "  ⚠ Use conflicted values with caution; recommend re-testing."
    )

    return "\n".join(lines)


def build_diet_prompt(
    aggregated_state: dict,
    per_doc_results: list[dict] | None = None,
) -> tuple[str, str]:
    """Build the system and user prompt pair for diet plan generation."""
    per_doc = per_doc_results or []

    patient_profile = _format_patient_profile(
        aggregated_state.get("patient_information", {}),
        aggregated_state.get("bmi"),
    )

    lab_results = _format_lab_results(
        aggregated_state.get("aggregated_tests", {}),
    )

    abnormal_findings = _format_abnormal_findings(
        aggregated_state.get("aggregated_abnormal_findings", []),
    )

    chronic_conditions = _format_chronic_conditions(
        aggregated_state.get("chronic_flags", []),
    )

    medications = _format_medications(per_doc)
    diagnoses = _format_diagnoses(per_doc)
    conflicts = _format_conflicts(
        aggregated_state.get("conflicts", []),
    )

    user_prompt = DIET_USER_PROMPT_TEMPLATE.format(
        patient_profile=patient_profile,
        lab_results=lab_results,
        abnormal_findings=abnormal_findings,
        chronic_conditions=chronic_conditions,
        medications=medications,
        diagnoses=diagnoses,
        conflicts=conflicts,
    )

    logger.info(
        "Diet prompt built: %d chars system, %d chars user",
        len(DIET_SYSTEM_PROMPT), len(user_prompt),
    )

    return DIET_SYSTEM_PROMPT, user_prompt
