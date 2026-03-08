import pickle
import numpy as np
import os
import pandas as pd

class HealthPredictor:
    def __init__(self, model_path='data/models/health_model.pkl'):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}. Run train_model.py first.")
        
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.models = model_data['models']
        self.features = model_data['features']
        self.conditions = model_data['conditions']
    
    def prepare_features(self, lab_values):
        features = []
        for feat in self.features:
            if feat in lab_values:
                features.append(lab_values[feat]['value'])
            else:
                features.append(0)
        return pd.DataFrame([features], columns=self.features)
    
    def predict(self, lab_values):
        X = self.prepare_features(lab_values)
        predictions = {}
        
        for condition in self.conditions:
            model = self.models[condition]
            prob = model.predict_proba(X)[0][1]
            
            if prob > 0.7:
                risk = 'high'
            elif prob > 0.4:
                risk = 'medium'
            else:
                risk = 'low'
            
            predictions[condition] = {
                'probability': float(prob),
                'risk': risk,
                'detected': bool(prob > 0.5)
            }
        
        return predictions
    
    def get_recommendations(self, predictions):
        recommendations = []
        
        if predictions.get('diabetes', {}).get('detected'):
            recommendations.append("Monitor blood sugar regularly")
            recommendations.append("Follow low-carb diet")
        
        if predictions.get('hypertension', {}).get('detected'):
            recommendations.append("Reduce sodium intake")
            recommendations.append("Regular exercise recommended")
        
        if predictions.get('high_cholesterol', {}).get('detected'):
            recommendations.append("Limit saturated fats")
            recommendations.append("Increase fiber intake")
        
        return recommendations

if __name__ == "__main__":
    predictor = HealthPredictor()
    
    sample_labs = {
        'glucose': {'value': 145},
        'bmi': {'value': 28},
        'age': {'value': 45},
        'bp_systolic': {'value': 140},
        'cholesterol': {'value': 220},
        'hdl': {'value': 45},
        'ldl': {'value': 150},
        'triglycerides': {'value': 180}
    }
    
    predictions = predictor.predict(sample_labs)
    print("ML Predictions:")
    for condition, result in predictions.items():
        print(f"  {condition}: {result['probability']:.0%} ({result['risk']} risk)")
