import os
import sys
import logging
import fitz  # PyMuPDF
import pandas as pd

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_pdf_to_excel(input_path: str, output_path: str):
    """
    Converts tables from a PDF file to Excel (XLSX) using PyMuPDF and pandas.
    """
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    
    try:
        logger.info(f"Starting PDF to Excel conversion. Input: {input_path}, Output: {output_path}")
        
        with fitz.open(input_path) as doc:
            if doc.needs_pass:
                doc.authenticate('')
                if doc.needs_pass:
                    raise RuntimeError("PDF is encrypted and cannot be parsed for tables without a password.")
                    
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                tables_found = False
                for page_num, page in enumerate(doc):
                    tabs = page.find_tables()
                    if tabs:
                        for tab_idx, tab in enumerate(tabs.tables):
                            df = tab.to_pandas()
                            sheet_name = f"Page_{page_num+1}_Table_{tab_idx+1}"
                            # Excel sheet names must be <= 31 chars
                            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                            tables_found = True
                            
                # Handle cases where no tables are found
                if not tables_found:
                    logger.warning("No tables were found in the PDF. Creating an empty sheet to prevent errors.")
                    pd.DataFrame(["No tables detected in PDF"]).to_excel(writer, sheet_name="Sheet1", index=False)
        
        if not os.path.exists(output_path):
            logger.error("Output file not found after conversion.")
            raise FileNotFoundError("PDF to Excel conversion failed.")
            
        logger.info("Conversion completed successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.exception(f"Exception during PDF to Excel conversion: {str(e)}")
        raise RuntimeError(f"PyMuPDF/pandas table extraction error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: python converter_pdf2excel.py <girdi_pdf> <çıktı_xlsx>")
        sys.exit(1)
    
    convert_pdf_to_excel(sys.argv[1], sys.argv[2])
