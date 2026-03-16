from ocr_module import extract_text_from_image

file_path = "sample_report.png"

text = extract_text_from_image(file_path)

print("Extracted Medical Report Text:")
print(text)
