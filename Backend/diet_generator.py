import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_diet_plan(analysis_text, diet_type):

    # Limit text size to avoid token errors
    analysis_text = analysis_text[:2000]

    prompt = f"""
You are a professional clinical nutritionist.

Based on the following medical analysis, create a structured 3-day personalized diet plan.

Medical Analysis:
{analysis_text}

Patient Diet Preference: {diet_type}

Instructions:
- If Vegetarian → include only vegetarian foods.
- If Non-Vegetarian → you may include eggs, chicken, or fish.
- Ensure the diet supports the patient's health condition.
- Avoid foods harmful for the detected risks.

Provide the output in this format:

Day 1
Breakfast:
Lunch:
Snack:
Dinner:

Day 2
Breakfast:
Lunch:
Snack:
Dinner:

Day 3
Breakfast:
Lunch:
Snack:
Dinner:
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )

    return response.choices[0].message.content