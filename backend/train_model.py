import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# ✅ Load Dataset
df = pd.read_csv("data/AI_NutriCare_Final_Advanced_1000.csv")

# ✅ Explicit Feature Selection (VERY IMPORTANT 🔥)
features = [
    "Hemoglobin",
    "RBC",
    "WBC",
    "Platelets",
    "Vitamin_D",
    "Creatinine",
    "MCV",
    "MCH"
]

X = df[features]
y = df["Condition"]

# ✅ Split Data
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)

# ✅ Model (Tuned Slightly Better)
model = RandomForestClassifier(
    n_estimators=150,
    random_state=42
)

# ✅ Train Model
model.fit(X_train, y_train)

# ✅ Accuracy
accuracy = model.score(X_test, y_test)
print("\nModel Accuracy:", accuracy)

# ✅ Save Model
with open("models/health_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("Model Saved Successfully ✅")