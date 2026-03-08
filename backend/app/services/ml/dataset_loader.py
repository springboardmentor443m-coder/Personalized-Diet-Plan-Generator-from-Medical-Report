import pandas as pd
import numpy as np
from sklearn.datasets import load_diabetes
import os

class DatasetLoader:
    def __init__(self, output_dir='data/datasets'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def create_diabetes_dataset(self):
        data = {
            'glucose': np.random.randint(70, 200, 1000),
            'bmi': np.random.uniform(18, 40, 1000),
            'age': np.random.randint(20, 80, 1000),
            'bp_systolic': np.random.randint(90, 180, 1000),
            'cholesterol': np.random.randint(150, 300, 1000),
            'hdl': np.random.randint(30, 80, 1000),
            'ldl': np.random.randint(70, 200, 1000),
            'triglycerides': np.random.randint(80, 300, 1000),
        }
        
        df = pd.DataFrame(data)
        
        df['diabetes'] = ((df['glucose'] > 125) | (df['bmi'] > 30)).astype(int)
        df['hypertension'] = (df['bp_systolic'] > 130).astype(int)
        df['high_cholesterol'] = (df['cholesterol'] > 240).astype(int)
        
        noise = np.random.random(len(df)) < 0.15
        df.loc[noise, 'diabetes'] = 1 - df.loc[noise, 'diabetes']
        
        return df
    
    def load_and_prepare(self):
        print("Generating medical dataset...")
        df = self.create_diabetes_dataset()
        
        output_path = f"{self.output_dir}/medical_data.csv"
        df.to_csv(output_path, index=False)
        print(f"Dataset saved: {output_path}")
        print(f"Total samples: {len(df)}")
        print(f"Features: {list(df.columns[:8])}")
        print(f"Conditions: diabetes, hypertension, high_cholesterol")
        
        return df

if __name__ == "__main__":
    loader = DatasetLoader()
    loader.load_and_prepare()
