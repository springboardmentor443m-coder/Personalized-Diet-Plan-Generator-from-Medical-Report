import re

def analyze_numeric_values(text):
    result = {
        "Blood Sugar": "Not Found",
        "Cholesterol": "Not Found",
        "BMI": "Not Found",
        "Risk Level": "Low"
    }

    lower_text = text.lower()

    # ---- Blood Sugar Detection ----
    if "sugar" in lower_text:
        result["Blood Sugar"] = "Mentioned"

    # ---- Cholesterol Detection ----
    if "cholesterol" in lower_text:
        result["Cholesterol"] = "Mentioned"

    # ---- BMI Extraction ----
    bmi_match = re.search(r"bmi[:\s]*([\d.]+)", lower_text)

    if bmi_match:
        bmi_value = float(bmi_match.group(1))

        if bmi_value < 18.5:
            result["BMI"] = f"{bmi_value} (Underweight)"
        elif 18.5 <= bmi_value <= 24.9:
            result["BMI"] = f"{bmi_value} (Normal)"
        elif 25 <= bmi_value <= 29.9:
            result["BMI"] = f"{bmi_value} (Overweight)"
        else:
            result["BMI"] = f"{bmi_value} (Obese)"

    # ---- Risk Level Logic ----
    if "diabetes" in lower_text or "high cholesterol" in lower_text:
        result["Risk Level"] = "High"
    elif result["BMI"] != "Not Found" and "Obese" in result["BMI"]:
        result["Risk Level"] = "High"
    else:
        result["Risk Level"] = "Moderate"

    return result