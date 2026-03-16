import pytesseract
import cv2
from PIL import Image

def extract_text_from_image(image_path):
    image = cv2.imread(image_path)
    text = pytesseract.image_to_string(image)
    return text
