import os

from rag.pdf_loader import load_pdf
from loaders.docx_loader import load_docx
from loaders.txt_loader import load_txt
from loaders.csv_loader import load_csv
from loaders.excel_loader import load_excel
from loaders.image_loader import load_image


def load_document(file_path):

    extension = os.path.splitext(
        file_path
    )[1].lower()

    if extension == ".pdf":
        return load_pdf(file_path)

    elif extension == ".docx":
        return load_docx(file_path)

    elif extension == ".txt":
        return load_txt(file_path)

    elif extension == ".csv":
        return load_csv(file_path)

    elif extension == ".xlsx":
        return load_excel(file_path)

    elif extension in [".png", ".jpg", ".jpeg"]:
        return load_image(file_path)

    else:
        raise Exception(
            f"{extension} not supported"
        )