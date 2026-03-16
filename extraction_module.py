import re

def extract_health_data(text):
    data = {}

    glucose = re.search(r'Glucose\s*:\s*(\d+)', text)
    cholesterol = re.search(r'Cholesterol\s*:\s*(\d+)', text)

    if glucose:
        data["Glucose"] = int(glucose.group(1))

    if cholesterol:
        data["Cholesterol"] = int(cholesterol.group(1))

    return data
