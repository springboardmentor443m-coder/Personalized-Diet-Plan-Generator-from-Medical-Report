import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb

# ==========================================
# CONFIGURATION
# ==========================================
DATA_DIR = "data"
MODEL_DIR = "models"

if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

print("🚀 Starting Model Training Process...")

# ==========================================
# 1. TRAIN DIABETES MODEL (PIMA DATASET)
# ==========================================
print("\n🔹 Training Diabetes Model...")
try:
    diabetes_path = os.path.join(DATA_DIR, 'diabetes.csv')
    df_diabetes = pd.read_csv(diabetes_path)
    
    # Preprocessing
    # Replacing zero values with NaN and then mean (common practice for PIMA)
    zero_cols = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
    for col in zero_cols:
        df_diabetes[col] = df_diabetes[col].replace(0, np.nan)
        df_diabetes[col].fillna(df_diabetes[col].mean(), inplace=True)
        
    X = df_diabetes.drop('Outcome', axis=1)
    y = df_diabetes['Outcome']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Using XGBoost for better performance
    model_diabetes = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss')
    model_diabetes.fit(X_train, y_train)
    
    # Evaluation
    preds = model_diabetes.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"✅ Diabetes Model Accuracy: {acc*100:.2f}%")
    
    # Save Model
    joblib.dump(model_diabetes, os.path.join(MODEL_DIR, 'diabetes_model.pkl'))
    print("💾 Saved to models/diabetes_model.pkl")
    
except Exception as e:
    print(f"❌ Error training Diabetes model: {e}")
    print("⚠️ Make sure 'diabetes.csv' is in the 'data' folder!")

# ==========================================
# 2. TRAIN HEART DISEASE MODEL (COMBINED/SINGLE)
# ==========================================
print("\n🔹 Training Heart Disease Model...")
try:
    # We will prioritize the heart_disease.csv (JohnSmith88) as it's standard
    # You can merge heart_attack.csv if columns match, but for simplicity, we use one robust dataset here.
    heart_path = os.path.join(DATA_DIR, 'heart_disease.csv')
    df_heart = pd.read_csv(heart_path)
    
    # Preprocessing
    X = df_heart.drop('target', axis=1)
    y = df_heart['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Using Random Forest
    model_heart = RandomForestClassifier(n_estimators=100, random_state=42)
    model_heart.fit(X_train, y_train)
    
    # Evaluation
    preds = model_heart.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"✅ Heart Disease Model Accuracy: {acc*100:.2f}%")
    
    # Save Model
    joblib.dump(model_heart, os.path.join(MODEL_DIR, 'heart_model.pkl'))
    print("💾 Saved to models/heart_model.pkl")

except Exception as e:
    print(f"❌ Error training Heart Disease model: {e}")
    print("⚠️ Make sure 'heart_disease.csv' is in the 'data' folder!")

print("\n🎉 All processes completed. You can now run 'streamlit run streamlit_app.py'")
