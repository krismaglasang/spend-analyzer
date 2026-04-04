import os

import pdfplumber
from dotenv import load_dotenv

load_dotenv()


def extract_text() -> list[str]:
    file_path = os.getenv("SAMPLE_PDF_FILE_PATH") or ""
    with pdfplumber.open(path_or_fp=file_path) as pdf:
        return [page.extract_text() for page in pdf.pages]
