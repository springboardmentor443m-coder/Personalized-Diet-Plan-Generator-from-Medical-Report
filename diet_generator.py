def generate_diet(condition):

    if "Possible Diabetes" in condition:
        return "Oatmeal, vegetables, whole grains"

    if "High Cholesterol" in condition:
        return "Fruits, nuts, olive oil, fish"

    return "Balanced diet"
