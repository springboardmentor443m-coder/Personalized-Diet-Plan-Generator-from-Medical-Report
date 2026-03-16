def chatbot_response(condition):

    if "Possible Diabetes" in condition:
        return "Avoid sugary foods and include whole grains, vegetables, and lean proteins."

    elif "High Cholesterol" in condition:
        return "Eat more fruits, nuts, olive oil, and reduce fried foods."

    else:
        return "Maintain a balanced diet and regular exercise."
