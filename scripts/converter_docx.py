import os
import logging
import pypandoc

logger = logging.getLogger(__name__)

def convert_docx_to_pdf(input_path: str, output_path: str):
    """
    Converts a DOCX file to PDF using pypandoc.
    Requires pandoc and a PDF engine (e.g. wkhtmltopdf, weasyprint, or pdflatex) installed on the system.
    """
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    
    try:
        logger.info(f"Attempting DOCX to PDF conversion using pypandoc: {input_path}")
        # Note: In a cloud environment like Render, you might need to specify the pdf-engine
        # For this script we rely on the default engine pandoc resolves in the environment.
        pypandoc.convert_file(
            input_path, 
            'pdf', 
            outputfile=output_path, 
            extra_args=['--pdf-engine=weasyprint']
        )
    except Exception as e:
        logger.error(f"pypandoc failed to convert DOCX to PDF: {e}")
        raise RuntimeError(f"pypandoc failed to convert DOCX to PDF: {e}")
            
    if not os.path.exists(output_path):
        raise FileNotFoundError("Conversion failed. PDF not found.")

