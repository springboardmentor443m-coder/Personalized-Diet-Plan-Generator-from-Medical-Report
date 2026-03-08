import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle
import os

class HealthModelTrainer:
    def __init__(self):
        self.models = {}
        self.feature_cols = ['glucose', 'bmi', 'age', 'bp_systolic', 'cholesterol', 'hdl', 'ldl', 'triglycerides']
        self.conditions = ['diabetes', 'hypertension', 'high_cholesterol']
    
    def load_data(self, csv_path):
        df = pd.read_csv(csv_path)
        df = df.fillna(df.mean())
        return df
    
    def train_model(self, condition, X_train, y_train):
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train, y_train)
        return model
    
    def train_all(self, data_path):
        df = self.load_data(data_path)
        X = df[self.feature_cols]
        
        results = {}
        
        for condition in self.conditions:
            print(f"\nTraining model for: {condition}")
            y = df[condition]
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            model = self.train_model(condition, X_train, y_train)
            
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            self.models[condition] = model
            results[condition] = accuracy
            
            print(f"Accuracy: {accuracy:.2%}")
        
        return results
    
    def save_models(self, output_dir='data/models'):
        os.makedirs(output_dir, exist_ok=True)
        
        model_data = {
            'models': self.models,
            'features': self.feature_cols,
            'conditions': self.conditions
        }
        
        model_path = f"{output_dir}/health_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"\nModels saved to: {model_path}")
        return model_path

if __name__ == "__main__":
    trainer = HealthModelTrainer()
    results = trainer.train_all('data/datasets/medical_data.csv')
    
    print("\n" + "="*50)
    print("TRAINING COMPLETE")
    print("="*50)
    for condition, acc in results.items():
        print(f"{condition}: {acc:.2%}")
    
    trainer.save_models()
