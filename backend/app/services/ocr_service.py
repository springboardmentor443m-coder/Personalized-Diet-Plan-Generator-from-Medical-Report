import pytesseract
import PyPDF2
from pdf2image import convert_from_path
import cv2
import os
import numpy as np
import string

class OCRService:
    def __init__(self):
        self.tesseract_config = "--oem 3 --psm 6"

    def extract_from_pdf(self, pdf_path):
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += (page.extract_text() or "") + "\n"
                
                if self._is_text_quality_usable(text):
                    return self._normalize_text(text)
                
                return self._ocr_from_pdf_images(pdf_path)
        except:
            return self._ocr_from_pdf_images(pdf_path)
    
    def _ocr_from_pdf_images(self, pdf_path):
        images = convert_from_path(pdf_path)
        text = ""
        for img in images:
            img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            processed = self._preprocess_image(img_bgr)
            text += pytesseract.image_to_string(processed, config=self.tesseract_config) + "\n"
        return self._normalize_text(text)
    
    def extract_from_image(self, image_path):
        img = cv2.imread(image_path)
        processed = self._preprocess_image(img)
        text = pytesseract.image_to_string(processed, config=self.tesseract_config)
        return self._normalize_text(text)

    def _preprocess_image(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, 15, 7, 21)
        scaled = cv2.resize(denoised, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        thresh = cv2.adaptiveThreshold(
            scaled,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11
        )
        return thresh

    def _normalize_text(self, text):
        text = text.replace('\x0c', '\n')
        text = text.replace('\r', '\n')
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return text

    def _is_text_quality_usable(self, text):
        stripped = text.strip()
        if len(stripped) < 80:
            return False

        weird_controls = sum(1 for char in text if ord(char) < 32 and char not in '\n\r\t')
        if weird_controls > 5:
            return False

        suspicious_chars = sum(1 for char in text if char not in string.printable and char not in '\n\r\t')
        if suspicious_chars > max(10, int(len(text) * 0.01)):
            return False

        return True
    
    def process_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self.extract_from_pdf(file_path)
        elif ext in ['.png', '.jpg', '.jpeg']:
            return self.extract_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
