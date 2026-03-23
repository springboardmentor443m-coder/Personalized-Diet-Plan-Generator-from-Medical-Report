"""
diet_planner.py - AI-NutriCare Personalized Diet Plan Generator

Takes extracted medical report data (from MedicalDocumentProcessor)
and user preferences, then generates a comprehensive 7-day diet plan
using Groq's LLaMA model.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -----------------------------------------------------------------------------
# BMI Calculation Utility
# -----------------------------------------------------------------------------
def compute_bmi_metrics(weight_kg: float, height_cm: float) -> Dict[str, Any]:
    height_m = height_cm / 100.0
    bmi_value = round(weight_kg / (height_m ** 2), 1)

    if bmi_value < 18.5:
        category = "Underweight"
        advice = "Increase calorie intake with nutrient-dense foods to gain healthy weight."
    elif bmi_value < 25:
        category = "Normal"
        advice = "Maintain current weight with a balanced diet and regular activity."
    elif bmi_value < 30:
        category = "Overweight"
        advice = "Reduce refined carbohydrates, increase fibre, and incorporate daily exercise."
    else:
        category = "Obese"
        advice = "Consult a healthcare provider; focus on a low-calorie, high-fibre diet."

    return {"bmi": bmi_value, "category": category, "advice": advice}


# -----------------------------------------------------------------------------
# Diet Plan Generator
# -----------------------------------------------------------------------------
class DietPlanGenerator:
    SYSTEM_PROMPT = """You are a certified clinical nutritionist specialising in Indian dietary patterns.
You will receive a patient's medical lab data, BMI information, and personal preferences.
Your task is to create a detailed, personalised 7-day diet plan.

Return ONLY valid JSON following the schema below. No additional text or markdown."""

    GENERATION_TEMPLATE = """
PATIENT DATA (JSON):
{patient_data_json}

USER PREFERENCES:
- Diet type: {diet_type}
- Height: {height_cm} cm, Weight: {weight_kg} kg, BMI: {bmi_value} ({bmi_category})
- Age: {age}, Gender: {gender}
- Allergies / foods to avoid: {allergies}

INSTRUCTIONS:
Based on the above, generate a comprehensive 7-day diet plan in the exact JSON format below.
Use only real Indian food items (e.g., dal, roti, sabzi, rice, idli, poha, upma).
If diet_type is "Vegetarian", exclude all meat, fish, eggs, and chicken.
If diet_type is "Non-Vegetarian", you may include lean meats, eggs, and fish appropriately.
Respect all allergies strictly.
Suggest actual Indian brands for supplements and packaged foods (e.g., Patanjali, Tata, Amul).

OUTPUT SCHEMA:
{{
  "patient_profile": {{
    "name": string,
    "age": number | null,
    "gender": string | null,
    "bmi": number,
    "bmi_category": string,
    "diet_type": string,
    "primary_concerns": [string]
  }},
  "nutrient_targets": {{
    "daily_calories": number,
    "protein_g": number,
    "carbs_g": number,
    "fats_g": number,
    "fiber_g": number,
    "water_liters": number,
    "notes": string
  }},
  "weekly_meal_plan": {{
    "monday":    {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "tuesday":   {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "wednesday": {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "thursday":  {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "friday":    {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "saturday":  {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "sunday":    {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }}
  }},
  "supplements": [
    {{ "name": string, "dosage": string, "reason": string, "indian_brand": string }}
  ],
  "zero_sugar_products": [
    {{ "product_name": string, "brand": string, "category": string, "why_recommended": string }}
  ],
  "indian_brand_suggestions": [
    {{ "product": string, "brand": string, "available_at": string, "benefit": string }}
  ],
  "hydration_detox_plan": {{
    "morning_ritual": string,
    "during_meals": string,
    "post_workout": string,
    "evening": string,
    "detox_drinks": [string],
    "foods_for_detox": [string],
    "weekly_detox_day": string
  }}
}}

Now generate the plan. Remember: ONLY valid JSON.
"""

    def __init__(self):           # fixed: was _init_
        self.client = groq_client

    def _prepare_patient_data(self, extracted_report: Dict[str, Any]) -> Dict[str, Any]:
        patient_info = extracted_report.get("patient_data", {})
        lab_results  = extracted_report.get("lab_results", {})
        abnormal     = extracted_report.get("abnormal_results", [])

        return {
            "patient_information": {
                "patient_name": patient_info.get("full_name"),
                "age_years":    patient_info.get("age_value"),
                "gender":       patient_info.get("gender"),
            },
            "tests_index": {
                k: {
                    "test_name":       v.get("test_name"),
                    "value":           v.get("value"),
                    "units":           v.get("unit"),
                    "reference_range": v.get("reference_range"),
                    "interpretation":  v.get("flag"),
                    "category":        v.get("category"),
                }
                for k, v in lab_results.items()
            },
            "abnormal_findings": [
                {
                    "canonical_test_key": a.get("test_key"),
                    "observed_value":     a.get("measured_value"),
                    "expected_range":     a.get("normal_interval"),
                    "severity":           a.get("severity"),
                }
                for a in abnormal
            ],
            "clinical_notes": extracted_report.get("clinical_notes", {}),
        }

    def generate_plan(self,
                      extracted_report: Dict[str, Any],
                      user_prefs: Dict[str, Any]) -> Dict[str, Any]:
        bmi_data = compute_bmi_metrics(
            weight_kg=user_prefs.get("weight_kg", 70),
            height_cm=user_prefs.get("height_cm", 170),
        )

        patient_data = self._prepare_patient_data(extracted_report)

        prompt = self.GENERATION_TEMPLATE.format(
            patient_data_json=json.dumps(patient_data, indent=2),
            diet_type=user_prefs.get("diet_type", "Vegetarian"),
            height_cm=user_prefs.get("height_cm", 170),
            weight_kg=user_prefs.get("weight_kg", 70),
            bmi_value=bmi_data["bmi"],
            bmi_category=bmi_data["category"],
            age=user_prefs.get("age", "unknown"),
            gender=user_prefs.get("gender", "unknown"),
            allergies=user_prefs.get("allergies", "none"),
        )

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.3,
                max_tokens=8000,
            )
        except Exception as e:
            return {"error": f"Groq API call failed: {str(e)}"}

        raw_output = response.choices[0].message.content

        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", raw_output).strip()
            start = cleaned.find("{")
            end   = cleaned.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("No JSON object found in response")
            json_str = cleaned[start:end + 1]
            json_str = re.sub(r",\s*}", "}", json_str)
            json_str = re.sub(r",\s*]", "]", json_str)
            diet_plan = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            return {
                "error": f"Failed to parse diet plan JSON: {str(e)}",
                "raw_output": raw_output,
            }

        diet_plan["_metadata"] = {
            "generated_at":  datetime.now().isoformat(),
            "bmi":           bmi_data["bmi"],
            "bmi_category":  bmi_data["category"],
            "source_file":   extracted_report.get("_metadata", {}).get("source_file"),
        }

        return diet_plan

    def save_plan(self, diet_plan: Dict[str, Any], filename: Optional[str] = None) -> str:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"diet_plan_{timestamp}.json"

        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(diet_plan, f, indent=2, ensure_ascii=False)

        print(f"💾 Diet plan saved to {output_path}")
        return str(output_path)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
if __name__ == "__main__":         # fixed: was _name_ / _main_
    import argparse

    parser = argparse.ArgumentParser(description="AI-NutriCare Diet Plan Generator")
    parser.add_argument("--report",    "-r", required=True)
    parser.add_argument("--diet",      "-d", choices=["Vegetarian", "Non-Vegetarian"], default="Vegetarian")
    parser.add_argument("--height",    type=float, required=True)
    parser.add_argument("--weight",    type=float, required=True)
    parser.add_argument("--age",       type=int)
    parser.add_argument("--gender",    choices=["male", "female", "other"])
    parser.add_argument("--allergies", default="")
    parser.add_argument("--output",    "-o")
    args = parser.parse_args()

    with open(args.report, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    prefs = {
        "diet_type": args.diet,
        "height_cm": args.height,
        "weight_kg": args.weight,
        "age":       args.age,
        "gender":    args.gender,
        "allergies": args.allergies,
    }

    generator = DietPlanGenerator()
    result = generator.generate_plan(report_data, prefs)

    if "error" in result:
        print(f"❌ {result['error']}")
        if "raw_output" in result:
            print("\nRaw LLM output:\n", result["raw_output"])
    else:
        saved = generator.save_plan(result, args.output)
        print(f"✅ Diet plan saved to: {saved}")