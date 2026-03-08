import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ml.dataset_loader import DatasetLoader
from app.services.ml.model_trainer import HealthModelTrainer

print("="*60)
print("WEEK 3-4: ML MODEL TRAINING")
print("="*60)

print("\nStep 1: Loading dataset...")
loader = DatasetLoader()
df = loader.load_and_prepare()

print("\nStep 2: Training ML models...")
trainer = HealthModelTrainer()
results = trainer.train_all('data/datasets/medical_data.csv')

print("\nStep 3: Saving models...")
trainer.save_models()

print("\n" + "="*60)
print("TRAINING COMPLETE - RESULTS")
print("="*60)
for condition, accuracy in results.items():
    status = "✓" if accuracy > 0.85 else "✗"
    print(f"{status} {condition.upper()}: {accuracy:.2%}")

avg_accuracy = sum(results.values()) / len(results)
print(f"\nAverage Accuracy: {avg_accuracy:.2%}")

if avg_accuracy > 0.85:
    print("\n✓ Milestone achieved: >85% accuracy")
else:
    print("\n✗ Below target accuracy")

print("\nNext: Start backend and generate a diet plan from the UI to validate predictions end-to-end.")
