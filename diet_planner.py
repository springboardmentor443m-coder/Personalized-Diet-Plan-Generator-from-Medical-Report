"""
diet_planner.py - AI-NutriCare Personalized Diet Plan Generator

This module takes extracted medical report data (from MedicalDocumentProcessor)
and user preferences, then generates a comprehensive 7‑day diet plan using
Groq's LLaMA model.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -----------------------------------------------------------------------------
# BMI Calculation Utility
# -----------------------------------------------------------------------------
def compute_bmi_metrics(weight_kg: float, height_cm: float) -> Dict[str, Any]:
    """
    Calculate BMI, category, and basic advice based on height and weight.
    """
    height_m = height_cm / 100.0
    bmi_value = round(weight_kg / (height_m ** 2), 1)

    if bmi_value < 18.5:
        category = "Underweight"
        advice = "Increase calorie intake with nutrient‑dense foods to gain healthy weight."
    elif bmi_value < 25:
        category = "Normal"
        advice = "Maintain current weight with a balanced diet and regular activity."
    elif bmi_value < 30:
        category = "Overweight"
        advice = "Reduce refined carbohydrates, increase fibre, and incorporate daily exercise."
    else:
        category = "Obese"
        advice = "Consult a healthcare provider; focus on a low‑calorie, high‑fibre diet."

    return {
        "bmi": bmi_value,
        "category": category,
        "advice": advice
    }


# -----------------------------------------------------------------------------
# Diet Plan Generator Class
# -----------------------------------------------------------------------------
class DietPlanGenerator:
    """
    Generates personalized diet plans using LLM based on lab report data and user preferences.
    """

    # System prompt for the LLM (slightly reworded from original)
    SYSTEM_PROMPT = """You are a certified clinical nutritionist specializing in Indian dietary patterns.
You will receive a patient's medical lab data, BMI information, and personal preferences.
Your task is to create a detailed, personalised 7‑day diet plan.

Return ONLY valid JSON following the schema below. No additional text or markdown."""

    # Generation prompt (modified but retains original JSON structure)
    GENERATION_TEMPLATE = """
PATIENT DATA (JSON):
{patient_data_json}

USER PREFERENCES:
- Diet type: {diet_type}
- Height: {height_cm} cm, Weight: {weight_kg} kg, BMI: {bmi_value} ({bmi_category})
- Age: {age}, Gender: {gender}
- Allergies / foods to avoid: {allergies}

INSTRUCTIONS:
Based on the above, generate a comprehensive 7‑day diet plan in the exact JSON format below.
Use only real Indian food items (e.g., dal, roti, sabzi, rice, idli, poha, upma).
If diet_type is "vegetarian", exclude all meat, fish, eggs, and chicken.
If diet_type is "non-vegetarian", you may include lean meats, eggs, and fish appropriately.
Respect all allergies strictly – never include any allergen.
Suggest actual Indian brands for supplements, zero‑sugar products, and packaged foods (e.g., Patanjali, Tata, Amul, etc.).

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
  "nutrition_targets": {{
    "daily_calories": number,
    "protein_g": number,
    "carbs_g": number,
    "fats_g": number,
    "fiber_g": number,
    "water_liters": number,
    "notes": string
  }},
  "foods_to_limit": [
    {{ "item": string, "reason": string }}
  ],
  "foods_to_emphasize": [
    {{ "item": string, "benefit": string }}
  ],
  "zero_sugar_recommendations": [
    {{
      "product": string,
      "brand": string,
      "category": string,
      "why": string
    }}
  ],
  "indian_brands": [
    {{
      "product": string,
      "brand": string,
      "availability": string,
      "benefit": string
    }}
  ],
  "supplement_advice": [
    {{ "name": string, "dosage": string, "purpose": string, "indian_brand": string }}
  ],
  "weekly_plan": {{
    "monday":    {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "tuesday":   {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "wednesday": {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "thursday":  {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "friday":    {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "saturday":  {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }},
    "sunday":    {{ "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }}
  }},
  "hydration_detox": {{
    "morning_ritual": string,
    "during_meals": string,
    "post_workout": string,
    "evening_routine": string,
    "detox_drinks": [string],
    "detox_foods": [string],
    "weekly_detox_day": string
  }},
  "lifestyle_guidance": [string]
}}

Now generate the plan. Remember: ONLY valid JSON.
"""

    def _init_(self):
        self.client = groq_client

    def _prepare_patient_data(self, extracted_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert the output of MedicalDocumentProcessor into a structure
        expected by the diet prompt.
        """
        # extracted_report comes from report_parser's process_document()
        patient_info = extracted_report.get("patient_data", {})
        lab_results = extracted_report.get("lab_results", {})
        abnormal = extracted_report.get("abnormal_results", [])

        # Build a simplified representation for the prompt
        return {
            "patient_information": {
                "patient_name": patient_info.get("full_name"),
                "age_years": patient_info.get("age_value"),
                "gender": patient_info.get("gender"),
            },
            "tests_index": {
                k: {
                    "test_name": v.get("test_name"),
                    "value": v.get("value"),
                    "units": v.get("unit"),
                    "reference_range": v.get("reference_range"),
                    "interpretation": v.get("flag"),
                    "category": v.get("category")
                }
                for k, v in lab_results.items()
            },
            "abnormal_findings": [
                {
                    "canonical_test_key": a.get("test_key"),
                    "observed_value": a.get("measured_value"),
                    "expected_range": a.get("normal_interval"),
                    "severity": a.get("severity")
                }
                for a in abnormal
            ],
            "clinical_notes": extracted_report.get("clinical_notes", {})
        }

    def generate_plan(self,
                      extracted_report: Dict[str, Any],
                      user_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method: takes extracted report and user preferences, returns diet plan JSON.
        user_prefs should contain: diet_type, height_cm, weight_kg, age, gender, allergies (string).
        """
        # 1. Calculate BMI
        bmi_data = compute_bmi_metrics(
            weight_kg=user_prefs.get("weight_kg", 70),
            height_cm=user_prefs.get("height_cm", 170)
        )

        # 2. Prepare patient data for prompt
        patient_data_for_prompt = self._prepare_patient_data(extracted_report)

        # 3. Build the full prompt
        prompt = self.GENERATION_TEMPLATE.format(
            patient_data_json=json.dumps(patient_data_for_prompt, indent=2),
            diet_type=user_prefs.get("diet_type", "vegetarian"),
            height_cm=user_prefs.get("height_cm", 170),
            weight_kg=user_prefs.get("weight_kg", 70),
            bmi_value=bmi_data["bmi"],
            bmi_category=bmi_data["category"],
            age=user_prefs.get("age", "unknown"),
            gender=user_prefs.get("gender", "unknown"),
            allergies=user_prefs.get("allergies", "none")
        )

        # 4. Call Groq API
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=8000
            )
        except Exception as e:
            return {"error": f"Groq API call failed: {str(e)}"}

        raw_output = response.choices[0].message.content

        # 5. Clean and parse JSON
        try:
            # Remove markdown code blocks
            cleaned = re.sub(r"json\s*|\s*", "", raw_output).strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("No JSON object found in response")
            json_str = cleaned[start:end+1]
            # Fix trailing commas
            json_str = re.sub(r",\s*}", "}", json_str)
            json_str = re.sub(r",\s*]", "]", json_str)
            diet_plan = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            return {
                "error": f"Failed to parse diet plan JSON: {str(e)}",
                "raw_output": raw_output
            }

        # 6. Add metadata (e.g., generation time, BMI info)
        diet_plan["_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "bmi": bmi_data["bmi"],
            "bmi_category": bmi_data["category"],
            "source_file": extracted_report.get("_metadata", {}).get("source_file")
        }

        return diet_plan

    def save_plan(self, diet_plan: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Save the generated diet plan to a JSON file in the 'output' directory.
        """
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
# CLI / Example Usage
# -----------------------------------------------------------------------------
if _name_ == "_main_":
    import argparse

    parser = argparse.ArgumentParser(description="AI-NutriCare Diet Plan Generator")
    parser.add_argument("--report", "-r", required=True, help="Path to extracted report JSON (from report_parser)")
    parser.add_argument("--diet", "-d", choices=["vegetarian", "non-vegetarian"], default="vegetarian")
    parser.add_argument("--height", type=float, required=True, help="Height in cm")
    parser.add_argument("--weight", type=float, required=True, help="Weight in kg")
    parser.add_argument("--age", type=int, help="Age")
    parser.add_argument("--gender", choices=["male", "female", "other"], help="Gender")
    parser.add_argument("--allergies", default="", help="Comma‑separated allergies")
    parser.add_argument("--output", "-o", help="Output JSON filename")

    args = parser.parse_args()

    # Load extracted report
    with open(args.report, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    # User preferences
    prefs = {
        "diet_type": args.diet,
        "height_cm": args.height,
        "weight_kg": args.weight,
        "age": args.age,
        "gender": args.gender,
        "allergies": args.allergies
    }

    # Generate plan
    generator = DietPlanGenerator()
    result = generator.generate_plan(report_data, prefs)

    if "error" in result:
        print(f"❌ {result['error']}")
        if "raw_output" in result:
            print("\nRaw LLM output:\n", result["raw_output"])
    else:
        # Save plan
        saved = generator.save_plan(result, args.output)
        print(f"\n✅ Diet plan generated and saved to: {saved}")

        # Quick summary
        profile = result.get("patient_profile", {})
        print(f"Patient: {profile.get('name', 'Unknown')}")
        print(f"BMI: {profile.get('bmi', '?')} ({profile.get('bmi_category', '?')})")
        print(f"Daily calories: {result.get('nutrition_targets', {}).get('daily_calories', '?')}")