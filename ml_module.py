def analyze_health(data):
    result = []

    if "Glucose" in data and data["Glucose"] > 126:
        result.append("Possible Diabetes")

    if "Cholesterol" in data and data["Cholesterol"] > 200:
        result.append("High Cholesterol")

    return result
