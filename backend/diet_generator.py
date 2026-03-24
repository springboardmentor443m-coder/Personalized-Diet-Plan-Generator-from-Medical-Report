from groq import Groq
from backend.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

DIET_PROMPT = """
You are a clinical nutrition assistant.

You are given the FULL OCR text of a diagnostic lab report.
First, understand the patient's health markers from the report.
Then generate a practical diet plan.

Guidelines:
- Base recommendations strictly on lab values found in the report
- Consider age, gender, and country
- Focus on food choices (no supplements or medicines)
- Be reassuring and non-alarming
- Write in a natural, ChatGPT-style tone

Include:
1. Brief health summary
2. Key nutrition focus areas
3. Foods to include
4. Foods to limit or avoid
5. Sample one-day meal plan (local to country)
6. Lifestyle food tips
7. Short disclaimer

Do not include any intro like "Here's your diet plan" - you are just a part of the application UI output.
"""


def calculate_bmi(weight: float, height: float) -> dict:
    """Calculate BMI and category."""
    # Safety check for zero height
    if height <= 0:
        return {"bmi": 0, "category": "Unknown"}
        
    height_m = height / 100  # Convert cm to meters
    bmi = weight / (height_m ** 2)
    
    # Determine BMI category
    if bmi < 18.5:
        category = "Underweight"
    elif 18.5 <= bmi < 25:
        category = "Normal weight"
    elif 25 <= bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    
    return {
        "bmi": round(bmi, 2),
        "category": category
    }


def generate_diet_plan(
    structured_data: dict,
    age: int,
    gender: str,
    country: str,
    weight: float,
    height: float,
    diet_preference: str
) -> str:
    """Generate personalized diet plan based on medical report and user data."""
    bmi_info = calculate_bmi(weight, height)
    
    # Convert structured data to string for the prompt
    data_str = str(structured_data)
    
    response = client.chat.completions.create(
        model=settings.DIET_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a clinical nutrition assistant."
            },
            {
                "role": "user",
                "content": f"""
Patient details:
- Age: {age}
- Gender: {gender}
- Country: {country}
- Weight: {weight} kg
- Height: {height} cm
- BMI: {bmi_info['bmi']} ({bmi_info['category']})
- Diet Preference: {diet_preference}

Medical report (structured data):
{data_str}

{DIET_PROMPT}
"""
            }
        ],
        temperature=0.7 
    )

    return response.choices[0].message.content.strip()