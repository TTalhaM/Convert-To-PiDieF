import os
import zipfile
import logging
import fitz  # PyMuPDF

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_pdf_to_jpg(input_path: str, temp_dir: str, base_name: str) -> list[str]:
    """
    Converts PDF pages to high-quality JPG images using PyMuPDF.
    Returns a list of generated JPG file paths.
    """
    input_path = os.path.abspath(input_path)
    temp_dir = os.path.abspath(temp_dir)
    image_files = []
    
    try:
        logger.info(f"Starting PDF to JPG conversion for {input_path}")
        with fitz.open(input_path) as doc:
            if doc.needs_pass:
                logger.info("PDF is encrypted, attempting to unlock with empty password.")
                doc.authenticate('')
                if doc.needs_pass:
                    raise RuntimeError("PDF is encrypted and cannot be unlocked with an empty password.")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Use high resolution zoom
                zoom = 2.0  # 2x zoom for better quality (roughly 144 DPI)
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                output_filename = f"{base_name}_page_{page_num + 1}.jpg"
                output_filepath = os.path.join(temp_dir, output_filename)
                
                pix.save(output_filepath)
                image_files.append(output_filepath)
                logger.debug(f"Saved {output_filepath}")
                
        logger.info(f"Conversion complete. Generated {len(image_files)} images.")
        return image_files
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.exception(f"Exception during PDF to JPG conversion: {str(e)}")
        raise RuntimeError(f"PyMuPDF convert error: {str(e)}")

