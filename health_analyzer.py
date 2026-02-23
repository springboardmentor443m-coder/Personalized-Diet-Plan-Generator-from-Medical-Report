import pickle
import numpy as np

class HealthAnalyzer:
    def __init__(self, model_path='xgboost_diabetes_model.pkl'):
        # Load the pre-trained XGBoost model
        with open(model_path, 'rb') as file:
            self.model = pickle.load(file)

    def predict_diabetes_risk(self, extracted_json):
        """
        Extracts relevant metrics from the Phase 1 JSON and runs inference.
        """
        # 1. Safely extract values from your JSON schema
        tests = extracted_json.get("tests_index", {})
        
        # We need to map your JSON keys to the features the model expects.
        # Note: A real model might require more features (BMI, Insulin, etc.). 
        # We use default/placeholder values for missing data to allow the model to run.
        glucose = tests.get("glucose_fasting", {}).get("value", 90.0) # From your JSON
        age = extracted_json.get("patient_information", {}).get("age_years", 30)
        
        # Example feature array: [Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigree, Age]
        # In a production app, you would extract all available metrics from the report.
        patient_features = np.array([[0, glucose, 80, 20, 0, 25.0, 0.5, age]])
        
        # 2. Run prediction
        prediction = self.model.predict(patient_features)
        risk_probability = self.model.predict_proba(patient_features)[0][1]
        
        # 3. Format result
        return {
            "condition": "Diabetes",
            "prediction_class": int(prediction[0]), # 1 = Risk, 0 = No Risk
            "risk_probability": round(risk_probability * 100, 2),
            "key_metrics_used": {"Glucose": glucose, "Age": age}
        }

# Example Usage (assuming final_result is the JSON from your notebook):
# analyzer = HealthAnalyzer()
# risk_assessment = analyzer.predict_diabetes_risk(final_result)
# print(risk_assessment)