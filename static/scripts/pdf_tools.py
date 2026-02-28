import os
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
import fitz  # PyMuPDF
from pdf2docx import Converter
import tempfile
import aspose.pdf as ap

def merge_pdfs(input_paths: list[str], output_path: str):
    """
    Merges multiple PDF files into one.
    """
    merger = PdfMerger()
    for path in input_paths:
        merger.append(path)
    
    merger.write(output_path)
    merger.close()

def split_pdf(input_path: str, output_dir: str, base_name: str) -> list[str]:
    """
    Splits a PDF file into separate single-page PDF files.
    Returns a list of generated file paths.
    """
    reader = PdfReader(input_path)
    output_files = []
    
    for i in range(len(reader.pages)):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])
        
        output_filename = f"{base_name}_page_{i+1}.pdf"
        output_filepath = os.path.join(output_dir, output_filename)
        
        with open(output_filepath, "wb") as f:
            writer.write(f)
            
        output_files.append(output_filepath)
        
    return output_files

def compress_pdf(input_path: str, output_path: str, level: str = 'medium'):
    """
    Compresses a PDF file using Aspose.PDF to control image_quality.
    Levels: 
    - low: Image quality 90 (High Quality)
    - medium: Image quality 60 (Recommended)
    - high: Image quality 30 (Small Size)
    """
    doc = ap.Document(input_path)
    optimization_options = ap.optimization.OptimizationOptions()
    
    optimization_options.link_duprates = True
    optimization_options.remove_unused_objects = True
    optimization_options.remove_unused_streams = True
    optimization_options.image_compression_options.compress_images = True
    
    if level == 'high':
        optimization_options.image_compression_options.image_quality = 30
        optimization_options.image_compression_options.resize_images = True
        optimization_options.image_compression_options.max_resolution = 150
    elif level == 'low':
        optimization_options.image_compression_options.image_quality = 90
        optimization_options.image_compression_options.resize_images = False
    else: # medium (default)
        optimization_options.image_compression_options.image_quality = 60
        optimization_options.image_compression_options.resize_images = True
        optimization_options.image_compression_options.max_resolution = 200

    doc.optimize_resources(optimization_options)
    doc.save(output_path)

def rotate_pdf(input_path: str, output_path: str, degrees: int = 90):
    """
    Rotates all pages in a PDF file clockwise by the specified degrees.
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.rotate(degrees)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

def watermark_pdf(input_path: str, output_path: str, watermark_text: str):
    """
    Adds a watermark text to all pages of a PDF file.
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Generate watermark PDF in memory
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # Set up transparent color
    transparent_gray = Color(0.5, 0.5, 0.5, alpha=0.3)
    can.setFillColor(transparent_gray)
    can.setFont("Helvetica-Bold", 60)
    
    # Draw centered, rotated text
    can.saveState()
    can.translate(300, 400) # approximate center
    can.rotate(45)
    can.drawCentredString(0, 0, watermark_text)
    can.restoreState()
    can.save()

    # Move to beginning of StringIO buffer
    packet.seek(0)
    watermark_pdf_reader = PdfReader(packet)
    watermark_page = watermark_pdf_reader.pages[0]

    for page in reader.pages:
        page.merge_page(watermark_page)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

def pdf_to_images(input_path: str, output_dir: str, base_name: str) -> list[str]:
    """
    Converts each page of a PDF to a JPG image using PyMuPDF.
    Returns a list of generated image file paths.
    """
    doc = fitz.open(input_path)
    output_files = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality (144 DPI)
        
        output_filename = f"{base_name}_page_{page_num+1}.jpg"
        output_filepath = os.path.join(output_dir, output_filename)
        
        pix.save(output_filepath)
        output_files.append(output_filepath)
        
    doc.close()
    return output_files

def encrypt_pdf(input_path: str, output_path: str, password: str):
    """
    Encrypts a PDF file with a password.
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(password)

    with open(output_path, "wb") as f:
        writer.write(f)

def decrypt_pdf(input_path: str, output_path: str, password: str):
    """
    Decrypts a PDF file with a password.
    Raises ValueError if password is wrong or PDF is not encrypted.
    """
    reader = PdfReader(input_path)
    
    if not reader.is_encrypted:
        raise ValueError("Bu PDF dosyası şifreli değil.")
        
    if not reader.decrypt(password):
        raise ValueError("Hatalı şifre girdiniz.")
        
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)
