import os
from PIL import Image

def convert_image_to_pdf(input_path: str, output_path: str):
    """
    Converts an image (PNG, JPG, JPEG) to PDF using Pillow.
    """
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    
    try:
        with Image.open(input_path) as image:
            # Convert to RGB to ensure compatibility with PDF format
            rgb_image = image.convert("RGB")
            rgb_image.save(output_path, "PDF", resolution=100.0)
    except Exception as e:
        raise RuntimeError(f"Image to PDF conversion failed: {e}")
    
    if not os.path.exists(output_path):
        raise FileNotFoundError("Image to PDF conversion failed, output missing.")
