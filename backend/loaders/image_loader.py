from PIL import Image
import pytesseract
from langchain.schema import Document

import os
_WIN = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(_WIN):
    pytesseract.pytesseract.tesseract_cmd = _WIN

def load_image(file_path):

    image = Image.open(file_path)

    image = image.convert("L")

    text = pytesseract.image_to_string(
        image,
        lang="eng"
    )

    return [
        Document(
            page_content=text
        )
    ]