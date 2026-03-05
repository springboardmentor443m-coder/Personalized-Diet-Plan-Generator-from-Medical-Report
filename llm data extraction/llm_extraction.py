from groq import Groq

client = Groq(api_key="Your ApI Key")

def extract_medical_values(text):

    # Reduce text size to avoid token limit
    text = text[:3000]

    prompt = f"""
    Extract medical test values from this report.

    Return ONLY JSON.

    Example format:
    {{
      "Hemoglobin": "",
      "Glucose": "",
      "Cholesterol": "",
      "Platelets": "",
      "Blood Pressure": ""
    }}

    Medical Report:
    {text}
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content