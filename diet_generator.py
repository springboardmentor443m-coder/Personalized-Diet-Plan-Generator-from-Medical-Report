import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environment variables (Make sure GROQ_API_KEY is in your .env file)
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class DietPlanGenerator:
    def __init__(self):
        self.model = "mixtral-8x7b-32768" # Fast and excellent at following JSON schemas

    def generate_plan(self, extracted_medical_data, ml_diagnosis):
        """
        Combines Phase 1 (Extracted JSON) and Phase 2 (ML Diagnosis) 
        to prompt the LLM for a personalized diet plan.
        """
        
        # 1. Isolate the unstructured clinical notes and abnormal findings
        clinical_notes = extracted_medical_data.get("clinical_notes", {})
        abnormal_findings = extracted_medical_data.get("abnormal_findings", [])
        
        # 2. Construct the strict prompt
        system_prompt = """
        You are an expert clinical nutritionist AI. Your job is to generate a personalized, 
        2-day diet plan based on a patient's medical report data and ML risk diagnosis.
        
        RULES:
        1. Address any 'abnormal_findings' (e.g., if Calcium is low, include dairy/leafy greens).
        2. Strictly follow any doctor recommendations found in 'clinical_notes'.
        3. Tailor the macros based on the 'ml_diagnosis' (e.g., if Diabetes risk is high, use low-GI foods).
        4. Output ONLY valid JSON using the exact schema provided. Do not include markdown formatting or explanations.
        
        JSON SCHEMA:
        {
            "patient_summary": "1 sentence overview of dietary focus",
            "detected_conditions": ["condition1", "condition2"],
            "diet_plan": {
                "day_1": {
                    "breakfast": "Meal description",
                    "lunch": "Meal description",
                    "snack": "Meal description",
                    "dinner": "Meal description"
                },
                "day_2": {
                    "breakfast": "Meal description",
                    "lunch": "Meal description",
                    "snack": "Meal description",
                    "dinner": "Meal description"
                }
            }
        }
        """

        user_prompt = f"""
        MEDICAL DATA:
        {json.dumps(abnormal_findings, indent=2)}
        
        DOCTOR'S NOTES:
        {json.dumps(clinical_notes, indent=2)}
        
        ML DIAGNOSIS:
        {json.dumps(ml_diagnosis, indent=2)}
        """

        print("Generating personalized diet plan... please wait.")
        
        # 3. Call the LLM
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2, # Low temperature for more deterministic, clinical outputs
        )
        
        # 4. Parse and return the JSON
        raw_output = response.choices[0].message.content.strip()
        
        # Safety clean-up in case the LLM wrapped it in markdown blocks
        if raw_output.startswith("```json"):
            raw_output = raw_output.replace("```json", "").replace("```", "").strip()
            
        return json.loads(raw_output)

# --- Example Execution ---
if __name__ == "__main__":
    # Mock data simulating what your Phase 1 & 2 scripts output
    sample_extracted_data = {
        "abnormal_findings": [
            {"canonical_test_key": "alkaline_phosphatase", "observed_value": 150.0, "severity": "high"},
            {"canonical_test_key": "calcium_total", "observed_value": 8.0, "severity": "low"}
        ],
        "clinical_notes": {
            "interpretations": ["HbA1c result is suggestive of well-controlled Diabetes in a known Diabetic"]
        }
    }
    
    sample_ml_diagnosis = {
        "condition": "Diabetes",
        "risk_probability": 88.5
    }

    generator = DietPlanGenerator()
    diet_plan = generator.generate_plan(sample_extracted_data, sample_ml_diagnosis)
    
    print("\n--- GENERATED DIET PLAN ---")
    print(json.dumps(diet_plan, indent=2))