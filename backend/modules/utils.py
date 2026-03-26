import re

def extract_metrics(text):
    if not text:
        return {}
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
        "Vitamin_D": r"(vitamin d|vitamin-d|vit d|vitd)[^\d]*(\d+\.?\d*)"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            try:
                metrics[key] = float(match.group(2))
            except:
                pass
    return metrics

def extract_metrics_from_json(structured_json):
    if not structured_json:
        return {}
    tests = structured_json.get("tests_index", {})
    metrics = {}
    for canonical_key, test_data in tests.items():
        value = test_data.get("value")
        if value is None:
            continue
        try:
            metrics[canonical_key] = float(value)
        except:
            metrics[canonical_key] = value
    return metrics
