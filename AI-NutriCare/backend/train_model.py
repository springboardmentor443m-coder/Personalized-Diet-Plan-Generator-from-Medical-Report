import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# Load Dataset
df = pd.read_csv("data/AI_NutriCare_Advanced_1000_Dataset.csv")

# Features & Target
X = df.drop("Condition", axis=1)
y = df["Condition"]

# Split Data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Model
model = RandomForestClassifier()

# Train
model.fit(X_train, y_train)

# Accuracy
accuracy = model.score(X_test, y_test)
print("Model Accuracy:", accuracy)

# Save Model
with open("models/health_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("Model Saved Successfully ✅")
