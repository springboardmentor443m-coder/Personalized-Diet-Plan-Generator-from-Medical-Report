from ocr_module import extract_text
from llm_extraction import extract_medical_values

file_path = "sample.pdf"

# Step 1: OCR extraction
text = extract_text(file_path)

# Step 2: LLM extraction
medical_data = extract_medical_values(text)

print("Extracted Medical Data:")
print(medical_data)