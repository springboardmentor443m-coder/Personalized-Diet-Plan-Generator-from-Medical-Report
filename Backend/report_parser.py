import pytesseract
from PIL import Image
import PyPDF2

# Tell Python where Tesseract is installed (Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text(uploaded_file):
    text = ""

    # If PDF
    if uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

    # If Image
    elif uploaded_file.type.startswith("image"):
        image = Image.open(uploaded_file)
        text = pytesseract.image_to_string(image)

    # If Text
    elif uploaded_file.type == "text/plain":
        text = uploaded_file.read().decode("utf-8")

    return text