import os
from pdf2docx import Converter

def convert_pdf_to_docx(input_path: str, output_path: str):
    """
    Converts a PDF file to DOCX using pdf2docx.
    """
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    
    try:
        cv = Converter(input_path)
        cv.convert(output_path, start=0, end=None)
        cv.close()
    except Exception as e:
        raise RuntimeError(f"PDF to DOCX conversion error: {str(e)}")
        
    if not os.path.exists(output_path):
        raise FileNotFoundError("PDF to DOCX conversion failed.")
