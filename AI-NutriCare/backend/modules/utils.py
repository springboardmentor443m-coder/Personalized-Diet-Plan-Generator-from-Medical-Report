import re

def extract_metrics(text):

    text = text.lower()

    metrics = {}

    patterns = {

        "Hemoglobin": r"(hemoglobin|haemoglobin)[^\d]*(\d+\.?\d*)",
        "RBC": r"(rbc)[^\d]*(\d+\.?\d*)",
        "WBC": r"(wbc)[^\d]*(\d+\.?\d*)",
        "Platelets": r"(platelet)[^\d]*(\d+)",
        "MCV": r"(mcv)[^\d]*(\d+\.?\d*)",
        "MCH": r"(mch)[^\d]*(\d+\.?\d*)",
        "Creatinine": r"(creatinine)[^\d]*(\d+\.?\d*)",
        "VitaminD": r"(vitamin d)[^\d]*(\d+\.?\d*)"
    }

    for key, pattern in patterns.items():

        match = re.search(pattern, text)

        if match:
            value = float(match.group(2))
            metrics[key] = value

    return metrics
