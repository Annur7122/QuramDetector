import pytesseract
from PIL import Image
import os

def extract_text_from_image(image_path):
    """Извлекает текст из изображения"""
    try:
        image = Image.open(image_path)
        extracted_text = pytesseract.image_to_string(image).strip()
        return extracted_text
    except Exception as e:
        return str(e)
