import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def interpret_report(text):
    text = text[:3000]  # limit text to avoid token overflow
    prompt = f"""
    You are a professional medical AI assistant.

    Analyze the following medical report.
    - Identify diseases
    - Identify abnormal values
    - Summarize patient's health condition clearly

    Medical Report:
    {text}
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content