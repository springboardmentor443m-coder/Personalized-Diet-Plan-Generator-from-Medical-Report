import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ─────────────────────────────────────────────
# BMI CALCULATOR
# ─────────────────────────────────────────────
def calculate_bmi(weight_kg: float, height_cm: float) -> dict:
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5:
        category = "Underweight"
        advice = "Focus on calorie-dense nutritious foods to gain healthy weight."
    elif bmi < 25:
        category = "Normal"
        advice = "Maintain current weight with balanced nutrition."
    elif bmi < 30:
        category = "Overweight"
        advice = "Reduce refined carbs, increase fiber and physical activity."
    else:
        category = "Obese"
        advice = "Consult a doctor. Focus on low-calorie, high-fiber diet."
    return {"bmi": bmi, "category": category, "advice": advice}


# ─────────────────────────────────────────────
# DIET PLAN PROMPT
# ─────────────────────────────────────────────
DIET_PROMPT = """You are a certified clinical nutritionist and dietitian specializing in Indian diets.
You will be given a patient's medical lab report data, BMI info, and dietary preferences.
Generate a comprehensive, highly personalized diet plan.
Return ONLY valid JSON in the exact schema below. No explanation. No markdown.

OUTPUT SCHEMA:
{
  "patient_summary": {
    "name": string,
    "age": number | null,
    "gender": string | null,
    "bmi": number,
    "bmi_category": string,
    "diet_type": string,
    "key_concerns": [string]
  },

  "nutrient_targets": {
    "daily_calories": number,
    "protein_g": number,
    "carbs_g": number,
    "fats_g": number,
    "fiber_g": number,
    "water_liters": number,
    "notes": string
  },

  "foods_to_avoid": [
    { "food": string, "reason": string }
  ],

  "foods_to_include": [
    { "food": string, "benefit": string }
  ],

  "zero_sugar_products": [
    {
      "product_name": string,
      "brand": string,
      "category": string,
      "why_recommended": string
    }
  ],

  "indian_brand_suggestions": [
    {
      "product": string,
      "brand": string,
      "available_at": string,
      "benefit": string
    }
  ],

  "supplements": [
    { "name": string, "dosage": string, "reason": string, "indian_brand": string }
  ],

  "weekly_meal_plan": {
    "monday":    { "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string },
    "tuesday":   { "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string },
    "wednesday": { "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string },
    "thursday":  { "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string },
    "friday":    { "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string },
    "saturday":  { "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string },
    "sunday":    { "breakfast": string, "mid_morning": string, "lunch": string, "evening_snack": string, "dinner": string, "bedtime": string }
  },

  "hydration_detox_plan": {
    "morning_ritual": string,
    "during_meals": string,
    "post_workout": string,
    "evening": string,
    "detox_drinks": [string],
    "foods_for_detox": [string],
    "weekly_detox_day": string
  },

  "lifestyle_tips": [string]
}

STRICT RULES:
- If diet_type is vegetarian: NO chicken, fish, meat, eggs in meal plan
- If diet_type is non-vegetarian: include lean meats, eggs, fish appropriately
- Respect food allergies completely — never include allergens
- Use Indian food options (dal, roti, sabzi, rice, idli, poha, upma etc.)
- Zero sugar products must be real Indian market available brands
- Indian brand suggestions must be real, available brands (Patanjali, Tata, Amul, etc.)
- Return ONLY valid JSON. No extra text.
"""


def generate_diet_plan(report: dict, user_prefs: dict) -> dict:
    """
    report      : parsed lab report dict from extractor
    user_prefs  : { diet_type, height_cm, weight_kg, age, gender, allergies, bmi_data }
    """
    focused_input = {
        "patient_information": report.get("patient_information", {}),
        "abnormal_findings": report.get("abnormal_findings", []),
        "tests_index": {
            k: {
                "test_name": v.get("test_name"),
                "value": v.get("value"),
                "units": v.get("units"),
                "reference_range": v.get("reference_range"),
                "interpretation": v.get("interpretation"),
                "category": v.get("category")
            }
            for k, v in report.get("tests_index", {}).items()
        },
        "clinical_notes": report.get("clinical_notes", {}),
        "user_preferences": user_prefs
    }

    full_prompt = DIET_PROMPT + "\n\nPATIENT DATA:\n" + json.dumps(focused_input, indent=2)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON. No markdown. No text outside JSON."},
            {"role": "user", "content": full_prompt}
        ],
        temperature=0.3,
        max_tokens=8000
    )

    raw = response.choices[0].message.content
    raw = re.sub(r"```json|```", "", raw).strip()
    start, end = raw.find("{"), raw.rfind("}")
    json_str = raw[start:end + 1]
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    return json.loads(json_str)