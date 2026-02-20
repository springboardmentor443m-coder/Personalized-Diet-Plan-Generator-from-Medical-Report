import pickle
import pandas as pd

MODEL_PATH = "models/health_model.pkl"

def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

def predict_condition(metrics):

    model = load_model()

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

    # Fill Missing Values
    for feature in required_features:
        if feature not in metrics:
            metrics[feature] = 0

    input_data = pd.DataFrame([metrics])[required_features]

    prediction = model.predict(input_data)[0]

    return prediction
