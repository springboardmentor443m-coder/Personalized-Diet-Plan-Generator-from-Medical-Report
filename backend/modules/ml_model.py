import pickle
import pandas as pd
import os

MODEL_PATH = "models/health_model.pkl"

def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

def predict_condition(metrics):
    model = load_model()
    if not model:
        return "Unknown"

    required_features = [
        "Hemoglobin",
        "RBC",
        "WBC",
        "Platelets",
        "VitaminD",
        "Creatinine",
        "MCV",
        "MCH"
    ]

    for feature in required_features:
        if feature not in metrics:
            metrics[feature] = 0

    input_data = pd.DataFrame([metrics])[required_features]
    prediction = model.predict(input_data)[0]
    return prediction
