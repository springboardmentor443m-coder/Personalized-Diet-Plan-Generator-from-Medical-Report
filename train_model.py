import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle

def train_diabetes_model():
    print("Loading dataset...")
    # For this example, you will need a dataset like 'diabetes.csv'
    # You can download the Pima Indians Diabetes dataset from Kaggle
    df = pd.read_csv('diabetes.csv') 
    
    # Split data into features (X) and target label (y)
    # Assuming 'Outcome' is 1 for Diabetic, 0 for Non-Diabetic
    X = df.drop('Outcome', axis=1) 
    y = df['Outcome'] 
    
    # Split into training (80%) and testing (20%) sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training XGBoost model...")
    # Initialize and train the XGBoost model
    # We limit the depth to prevent overfitting
    model = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1)
    model.fit(X_train, y_train)
    
    # Evaluate the model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy: {accuracy * 100:.2f}%")
    
    # Save the trained model for later use
    with open('xgboost_diabetes_model.pkl', 'wb') as file:
        pickle.dump(model, file)
    print("Model saved to 'xgboost_diabetes_model.pkl'")

if __name__ == "__main__":
    train_diabetes_model()