import pdfplumber
import easyocr
import numpy as np
from PIL import Image
import io

reader = easyocr.Reader(['en'], gpu=False)

def extract_text(file, file_type):
    if file_type == "pdf":
        return extract_text_from_pdf(file)
    elif file_type in ["png", "jpg", "jpeg"]:
        return extract_text_from_image(file)
    elif file_type == "txt":
        return file.read().decode("utf-8")
    else:
        return ""

def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_text_from_image(file):
    image_bytes = file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_np = np.array(image)
    result = reader.readtext(image_np, detail=0)
    return " ".join(result)
