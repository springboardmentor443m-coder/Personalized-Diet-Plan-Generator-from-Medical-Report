import pdfplumber
import pytesseract
from PIL import Image
import cv2
import numpy as np
from pdf2image import convert_from_path
def preprocess_image(image):
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
    return thresh
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text
def extract_text(file_path):
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)

    elif file_path.endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(file_path)
        processed = preprocess_image(image)
        return pytesseract.image_to_string(processed)

    else:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()