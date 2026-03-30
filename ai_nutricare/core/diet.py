"""
core/diet.py
Steps 4-5: BMI Calculation + Diet Plan Generation (Llama 3.3 70B Versatile on Groq)
"""

import os
import json
from typing import Dict, Tuple

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Step 4: BMI ───────────────────────────────────────────────────────────────

def calculate_bmi(weight_kg: float, height_cm: float) -> Tuple[float, str]:
    """Return (bmi_value, category)."""
    h_m  = height_cm / 100
    bmi  = round(weight_kg / (h_m ** 2), 1)
    if bmi < 18.5:
        cat = "Underweight"
    elif bmi < 25:
        cat = "Normal"
    elif bmi < 30:
        cat = "Overweight"
    else:
        cat = "Obese"
    return bmi, cat


# ── Step 5: Diet Plan ────────────────────────────────────────────────────────

DIET_SYSTEM_PROMPT = """You are an expert clinical nutritionist and dietitian with deep knowledge of:
- Evidence-based medical nutrition therapy
- Cultural and regional food preferences
- The relationship between lab values and dietary requirements

You always generate personalized, practical, culturally appropriate diet plans.
You respond ONLY with valid JSON — no markdown, no preamble."""

def build_diet_prompt(extracted_data: Dict, profile: Dict) -> str:
    """Build the prompt for the diet plan generation."""

    patient  = extracted_data.get("patient_information", {})
    abnormal = extracted_data.get("abnormal_findings", [])
    tests    = extracted_data.get("tests_index", {})
    notes    = extracted_data.get("clinical_notes", {})

    # Build a concise lab summary for the prompt
    abnormal_summary = []
    for ab in abnormal:
        key  = ab["canonical_test_key"]
        meta = tests.get(key, {})
        abnormal_summary.append(
            f"- {meta.get('test_name', key)}: {ab['observed_value']} {meta.get('units','')} "
            f"(range {ab['expected_range']}, severity: {ab['severity']})"
        )

    ab_text    = "\n".join(abnormal_summary) if abnormal_summary else "None detected."
    interps    = "\n".join(notes.get("interpretations", []) + notes.get("recommendations", []))

    return f"""
Generate a comprehensive personalized diet plan based on the following patient data.

PATIENT PROFILE:
- Name: {patient.get('patient_name', 'Patient')}
- Age: {patient.get('age_years', 'Unknown')} years
- Gender: {patient.get('gender', 'Unknown')}
- Weight: {profile['weight_kg']} kg | Height: {profile['height_cm']} cm
- BMI: {profile['bmi']} ({profile['bmi_category']})
- Country / Food Culture: {profile['country']}
- Diet Preference: {profile['diet_preference']}

ABNORMAL LAB FINDINGS:
{ab_text}

CLINICAL NOTES & INTERPRETATIONS:
{interps if interps else 'None provided.'}

INSTRUCTIONS:
1. Analyze the lab values and identify nutrition-related issues.
2. Generate a diet plan tailored to the abnormal values, BMI, and food culture.
3. Include locally available foods from {profile['country']}.
4. Respect the {profile['diet_preference']} dietary preference.

Return ONLY the following JSON structure (no markdown, no extra text):
{{
  "health_summary": "2-3 sentence plain-language summary of the patient's health status based on lab results",
  "nutrition_focus_areas": ["area1", "area2", ...],
  "foods_to_include": ["food1 — reason", "food2 — reason", ...],
  "foods_to_avoid": ["food1 — reason", "food2 — reason", ...],
  "sample_meal_plan": {{
    "Day 1": {{
      "breakfast": "...",
      "mid_morning_snack": "...",
      "lunch": "...",
      "evening_snack": "...",
      "dinner": "..."
    }},
    "Day 2": {{ ... }},
    "Day 3": {{ ... }}
  }},
  "lifestyle_tips": ["tip1", "tip2", ...],
  "important_disclaimer": "This plan is AI-generated and should be reviewed by a qualified healthcare professional before implementation."
}}
"""


def generate_diet_plan(extracted_data: Dict, profile: Dict) -> Dict:
    """
    Call Llama 3.3 70B Versatile on Groq to generate a personalised diet plan.
    Returns a parsed dict with keys: health_summary, foods_to_include, etc.
    """
    prompt = build_diet_prompt(extracted_data, profile)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": DIET_SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=4096,
        temperature=0.4,
    )

    content = response.choices[0].message.content
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)
