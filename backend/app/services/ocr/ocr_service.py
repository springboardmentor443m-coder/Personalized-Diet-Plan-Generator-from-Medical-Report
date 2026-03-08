import pytesseract
import PyPDF2
from pdf2image import convert_from_path
import cv2
import os

class OCRService:
    def extract_from_pdf(self, pdf_path):
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                if len(text.strip()) > 50:
                    return text
                
                return self._ocr_from_pdf_images(pdf_path)
        except:
            return self._ocr_from_pdf_images(pdf_path)
    
    def _ocr_from_pdf_images(self, pdf_path):
        images = convert_from_path(pdf_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"
        return text
    
    def extract_from_image(self, image_path):
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        text = pytesseract.image_to_string(thresh)
        return text
    
    def process_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self.extract_from_pdf(file_path)
        elif ext in ['.png', '.jpg', '.jpeg']:
            return self.extract_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
