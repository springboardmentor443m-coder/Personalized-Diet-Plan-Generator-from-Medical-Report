import pytesseract
from pdf2image import convert_from_path
import re
from groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create Groq client using API key from .env
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def extract_data(pdf_path):

    # Convert PDF to images
    images = convert_from_path(
        pdf_path,
        poppler_path=r"C:\Users\ACER\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"
    )

    # Tesseract path
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    # OCR text extraction
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)

    print("OCR TEXT:\n", text[:500])

    # Regex patterns for extracting medical values
    patterns = {
        "hemoglobin": r'(?:Hemoglobin|Haemoglobin|Hb).*?(\d+\.?\d*)',
        "rbc": r'(?:RBC Count|RBC).*?(\d+\.?\d*)',
        "pcv": r'(?:Packed Cell Volume|PCV).*?(\d+\.?\d*)',
        "mcv": r'MCV.*?(\d+\.?\d*)',
        "mch": r'MCH.*?(\d+\.?\d*)',
        "mchc": r'MCHC.*?(\d+\.?\d*)'
    }

    medical_data = {}

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        medical_data[key] = match.group(1) if match else None

    # Health analysis
    analysis = {}

    if medical_data["hemoglobin"]:
        hb = float(medical_data["hemoglobin"])

        if hb < 13:
            analysis["hemoglobin"] = "Low (Possible Anemia)"
        elif hb > 17:
            analysis["hemoglobin"] = "High"
        else:
            analysis["hemoglobin"] = "Normal"

    # BMI calculation
    weight = 70
    height = 1.75

    bmi = weight / (height ** 2)

    if bmi < 18.5:
        bmi_category = "Underweight"
    elif bmi < 25:
        bmi_category = "Normal"
    elif bmi < 30:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obese"

    # Diet recommendation
    if analysis.get("hemoglobin") == "Low (Possible Anemia)":
        diet = [
            "Spinach",
            "Beetroot",
            "Dates",
            "Iron rich foods"
        ]
    else:
        diet = [
            "Balanced diet",
            "Vegetables",
            "Fruits",
            "Protein rich foods"
        ]

    # AI analysis using Groq
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": f"Analyze this medical report and explain key health insights:\n{text}"
            }
        ],
        temperature=0
    )

    ai_result = response.choices[0].message.content

    result = {
        "medical_values": medical_data,
        "health_analysis": analysis,
        "BMI": round(bmi, 2),
        "BMI_category": bmi_category,
        "diet_recommendation": diet,
        "ai_analysis": ai_result
    }

    return result