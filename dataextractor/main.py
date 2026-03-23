from ocr_module import extract_text
from data_extraction import extract_structured_data, save_json
from ml_model import predict_condition
from diet_recommender import recommend_diet


def main():

    file_path = "sample.pdf"   # your uploaded file

    print("Extracting text...")
    text = extract_text(file_path)

    print("\nExtracting structured data...")
    structured_data = extract_structured_data(text)

    print("\n--- STRUCTURED OUTPUT ---\n")
    print(structured_data)
    conditions = predict_condition(structured_data["lab_results"])
    print("\nPredicted Conditions:", conditions)

    diet_plan = recommend_diet(conditions)
    print("\nDiet Plan:", diet_plan)
    save_json(structured_data)

    print("\nOutput saved to output.json")


if __name__ == "__main__":
    main()