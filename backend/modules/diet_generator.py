import google.generativeai as genai
import os
import json

def generate_diet(condition, metrics=None, structured_data=None, dietary_preference="Non-Vegetarian"):
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        abnormal = []
        patient_info = {}
        if structured_data:
            abnormal = structured_data.get('abnormal_findings', [])
            patient_info = structured_data.get('patient_information', {})
            
        prompt = f"""
        Act as an expert clinical dietitian. Generate a strict JSON response containing a personalized nutritional protocol.
        
        Patient Medical Condition: {condition}
        Patient Dietary Preference: {dietary_preference}
        Patient Biomarkers & Abnormalities: {json.dumps(abnormal)}
        Patient Physical Context: {json.dumps(patient_info)}
        
        Output Requirements: Provide a JSON object exactly like this (no markdown formatting, no comments, just valid JSON):
        {{
            "executive_summary": "A 2-3 sentence clinical summary explaining the focus of this diet based on the provided biomarkers and condition.",
            "daily_plan": {{
                "breakfast": "• Point 1 (Ingredients)\\n• Point 2 (Preparation)\\n• Point 3 (Portion)",
                "lunch": "• Point 1 (Ingredients)\\n• Point 2 (Preparation)\\n• Point 3 (Portion)",
                "dinner": "• Point 1 (Ingredients)\\n• Point 2 (Preparation)\\n• Point 3 (Portion)",
                "snacks": "• Point 1 (Options)\\n• Point 2 (Timing)"
            }},
            "superfoods": ["1", "2", "3", "4", "5", "6", "7", "8"],
            "foods_to_avoid": ["1", "2", "3", "4", "5", "6", "7", "8"]
        }}
        
        CRITICAL INSTRUCTIONS:
        - The `daily_plan` values MUST be comprehensive, longer, and formatted exactly point-by-point using bullet points (•) and newline (\\n) characters as shown above.
        - You MUST provide EXACTLY 8 items in the `superfoods` array.
        - You MUST provide EXACTLY 8 items in the `foods_to_avoid` array.
        """
        
        response = model.generate_content(prompt)
        content = response.text
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        diet_plan = json.loads(content)
        return diet_plan
        
    except Exception as e:
        print("Diet Generator Error:", e)
        return {
            "executive_summary": f"Baseline nutritional maintenance recommended for {condition} ({dietary_preference}). Consult your doctor for an AI disruption.",
            "daily_plan": {
                "breakfast": "Balanced Meal (Oats & Fruit)",
                "lunch": "Lean Protein & Greens",
                "dinner": "Light Vegetable Soup / Stew",
                "snacks": "Nuts & Seeds"
            },
            "superfoods": ["Water", "Green Veggies"],
            "foods_to_avoid": ["Excessive Sugar", "Processed Foods"]
        }
