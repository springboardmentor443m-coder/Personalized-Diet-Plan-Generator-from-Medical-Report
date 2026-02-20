import pdfplumber
import easyocr
import numpy as np
import cv2
from PIL import Image

# ✅ Initialize OCR Reader ONCE
reader = easyocr.Reader(['en'], gpu=False)


def extract_text(file, file_type):

    file_type = file_type.lower()

    if file_type == "pdf":
        return extract_text_from_pdf(file)

    elif file_type == "txt":
        return str(file.read(), "utf-8")

    elif file_type in ["png", "jpg", "jpeg"]:
        return extract_text_from_image(file)

    else:
        return "Unsupported File Type"


def extract_text_from_pdf(file):

    text = ""

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return text


def extract_text_from_image(file):

    image = Image.open(file)

    # ✅ CRITICAL FIX — Convert RGBA → RGB 🔥
    image = image.convert("RGB")

    image = np.array(image)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # ✅ Improve OCR Accuracy 🔥
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5)
    gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=20)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    result = reader.readtext(gray, detail=0)

    return " ".join(result)
