import os
import uuid
import asyncio
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import zipfile
import magic

# Aspose modules are isolated in subprocesses using venv_words and venv_slides
from scripts.converter_image import convert_image_to_pdf
from scripts.pdf_tools import (
    merge_pdfs, split_pdf, compress_pdf, rotate_pdf, watermark_pdf,
    pdf_to_images, encrypt_pdf, decrypt_pdf
)

def validate_file_type(file_bytes: bytes, expected_ext: str = None) -> str:
    """
    Validates file type using python-magic.
    Raises HTTPException if invalid. Returns the mime type.
    """
    mime_type = magic.from_buffer(file_bytes, mime=True)
    
    # Generic security check for risky files
    risky_mimes = ['application/x-executable', 'application/x-sh', 'application/x-bat']
    if mime_type in risky_mimes:
         raise HTTPException(status_code=400, detail="Güvenlik nedeniyle bu dosya türüne izin verilmiyor.")
         
    return mime_type

app = FastAPI(title="Modern File Converter & PDF Tools")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
CONVERTED_DIR = os.path.join(os.getcwd(), "converted")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

async def delete_files_after_delay(filepaths: list[str], delay_seconds: int = 600):
    """Deletes the specified files after a delay (10 minutes default)."""
    await asyncio.sleep(delay_seconds)
    for path in filepaths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Failed to delete {path}: {e}")

@app.options("/preview/")
@app.post("/preview/")
async def preview_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Önizleme sadece PDF dosyaları için destekleniyor.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Dosya boyutu 너무 büyük.")

    import fitz # PyMuPDF
    import base64

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if doc.needs_pass:
            return JSONResponse(content={"error": "locked"})
        
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5), alpha=False)
        img_bytes = pix.tobytes("jpeg")
        b64_str = base64.b64encode(img_bytes).decode('utf-8')
        doc.close()
        
        return JSONResponse(content={"thumbnail": f"data:image/jpeg;base64,{b64_str}"})
    except Exception as e:
        print(f"Preview Error: {e}")
        return JSONResponse(content={"error": "failed"})

@app.options("/upload/")
@app.post("/upload/")
async def upload_file(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...), target_format: str = Form(None)):
    if not files:
        raise HTTPException(status_code=400, detail="Dosya yüklenmedi.")
        
    _id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_DIR, _id)
    os.makedirs(temp_dir, exist_ok=True)
    
    out_dir = os.path.join(CONVERTED_DIR, _id)
    os.makedirs(out_dir, exist_ok=True)
    
    files_to_delete = [temp_dir, out_dir]
    processed_files = []
    import subprocess
    
    try:
        for idx, file in enumerate(files):
            file_bytes = await file.read()
            if len(file_bytes) > MAX_FILE_SIZE:
                 raise HTTPException(status_code=413, detail=f"'{file.filename}' boyutu 20MB sınırını aşıyor.")
                 
            mime_type = validate_file_type(file_bytes)
            
            ext = os.path.splitext(file.filename)[1].lower()
            base_name = os.path.splitext(file.filename)[0]
            
            input_path = os.path.join(temp_dir, f"{idx}_{base_name}{ext}")
            
            with open(input_path, "wb") as f:
                f.write(file_bytes)
            files_to_delete.append(input_path)
            
            # Use current target_format or decide default per file
            t_fmt = target_format
            if not t_fmt:
                if ext in [".docx", ".pptx", ".jpg", ".jpeg", ".png"]:
                    t_fmt = "pdf"
                elif ext == ".pdf":
                    t_fmt = "pptx"
                    
            if not t_fmt: continue
            t_fmt = t_fmt.lower()
            
            output_path = ""
            target_ext = ""
            
            if ext == ".docx":
                if t_fmt != "pdf":
                    raise HTTPException(status_code=400, detail="Word dosyaları sadece PDF formatına dönüştürülebilir.")
                target_ext = ".pdf"
                output_path = os.path.join(out_dir, f"{base_name}{target_ext}")
                venv_python = os.path.join(os.getcwd(), "venv_words", "Scripts", "python.exe")
                cmd = [venv_python, "-c", "import sys; from scripts.converter_docx import convert_docx_to_pdf; convert_docx_to_pdf(sys.argv[1], sys.argv[2])", input_path, output_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0: raise RuntimeError(f"DOCX Dönüşüm Hatası: {result.stderr}")
                
            elif ext == ".pptx":
                if t_fmt != "pdf":
                    raise HTTPException(status_code=400, detail="PowerPoint sadece PDF'e dönüştürülebilir.")
                target_ext = ".pdf"
                output_path = os.path.join(out_dir, f"{base_name}{target_ext}")
                venv_python = os.path.join(os.getcwd(), "venv_slides", "Scripts", "python.exe")
                cmd = [venv_python, "-c", "import sys; from scripts.converter_pptx import convert_pptx_to_pdf; convert_pptx_to_pdf(sys.argv[1], sys.argv[2])", input_path, output_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0: raise RuntimeError(f"PPTX Dönüşüm Hatası: {result.stderr}")
                
            elif ext == ".pdf":
                if t_fmt == "pptx":
                    target_ext = ".pptx"
                    output_path = os.path.join(out_dir, f"{base_name}{target_ext}")
                    venv_python = os.path.join(os.getcwd(), "venv_slides", "Scripts", "python.exe")
                    cmd = [venv_python, "-c", "import sys; from scripts.converter_pptx import convert_pdf_to_pptx; convert_pdf_to_pptx(sys.argv[1], sys.argv[2])", input_path, output_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0: raise RuntimeError(f"PDF->PPTX Hatası: {result.stderr}")
                elif t_fmt == "docx":
                    target_ext = ".docx"
                    output_path = os.path.join(out_dir, f"{base_name}{target_ext}")
                    venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
                    if not os.path.exists(venv_python):
                        import sys
                        venv_python = sys.executable
                    cmd = [venv_python, "-c", "import sys; from scripts.converter_pdf2docx import convert_pdf_to_docx; convert_pdf_to_docx(sys.argv[1], sys.argv[2])", input_path, output_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0: raise RuntimeError(f"PDF->DOCX Hatası: {result.stderr}")
                else:
                    raise HTTPException(status_code=501, detail=f"PDF'den '{t_fmt}' formatına dönüştürme desteklenmiyor.")
            elif ext in [".png", ".jpg", ".jpeg"]:
                target_ext = ".pdf"
                output_path = os.path.join(out_dir, f"{base_name}{target_ext}")
                convert_image_to_pdf(input_path, output_path)
                
            if output_path and os.path.exists(output_path):
                processed_files.append(output_path)
                files_to_delete.append(output_path)
                
    except Exception as e:
        background_tasks.add_task(delete_files_after_delay, files_to_delete, 0)
        raise HTTPException(status_code=500, detail=str(e))
        
    if not processed_files:
        raise HTTPException(status_code=400, detail="Dönüştürülecek dosya bulunamadı veya işlem başarısız.")
        
    final_output_filename = ""
    target_ext_msg = ""
    
    # Check if single file or multiple
    if len(processed_files) == 1:
        final_output_path = processed_files[0]
        final_output_filename = os.path.basename(final_output_path)
        # We don't zip a single file unless it's an image extraction (which /upload/ doesn't handle natively)
    else:
        # Zip multiple processed files
        zip_filename = f"converted_batch_{_id}.zip"
        zip_path = os.path.join(CONVERTED_DIR, zip_filename)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in processed_files:
                zipf.write(f, os.path.basename(f))
                
        final_output_filename = zip_filename
        files_to_delete.append(zip_path)

    # Schedule deletion
    background_tasks.add_task(delete_files_after_delay, files_to_delete, 600)
    
    return JSONResponse(content={
        "message": f"{len(processed_files)} dosya başarıyla dönüştürüldü!",
        "download_url": f"/download/{final_output_filename}",
        "original_filename": f"{len(files)} dosya işlendi",
        "converted_filename": final_output_filename
    })

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(CONVERTED_DIR, filename)
    # also check if the file is inside a temp dir
    if not os.path.exists(file_path):
        # We might need to search in subdirectories due to our new _id based folders for multiple single files.
        found = False
        if len(filename.split('_')) > 0: # single files are saved as base_name.pdf inside an _id dir mostly
             pass # Not heavily needed since we save zip to CONVERTED_DIR, and single files to out_dir
        
    # Standard logic: Since single files were generated inside CONVERTED_DIR\_id\filename, we actually need to change where single files are downloaded from.
    # To fix this simply, let's just make the /download route handle direct paths or search if it's not strictly found.
    # Wait, the best fix is to copy the single file back to CONVERTED_DIR.
    if not os.path.exists(file_path):
        # Search for it in subdirs
        for root, dirs, files in os.walk(CONVERTED_DIR):
            if filename in files:
                file_path = os.path.join(root, filename)
                break
                
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı veya süresi dolduğu için silindi.")
    
    return FileResponse(
        file_path, 
        filename=filename,
        media_type='application/octet-stream',
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.options("/merge/")
@app.post("/merge/")
async def merge_files(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Birleştirme işlemi için en az 2 PDF dosyası yüklemelisiniz.")
        
    input_paths = []
    _id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_DIR, _id)
    os.makedirs(temp_dir, exist_ok=True)
    
    for idx, file in enumerate(files):
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Sadece PDF dosyaları birleştirilebilir.")
            
        file_bytes = await file.read()
        if len(file_bytes) > MAX_FILE_SIZE:
             raise HTTPException(status_code=413, detail=f"Dosya '{file.filename}' boyutu 20MB sınırını aşıyor.")
             
        # Validate with magic
        mime_type = validate_file_type(file_bytes)
        if 'pdf' not in mime_type.lower():
            raise HTTPException(status_code=400, detail=f"'{file.filename}' geçerli bir PDF dosyası değil.")
             
        input_path = os.path.join(temp_dir, f"{idx}_{file.filename}")
        with open(input_path, "wb") as f:
            f.write(file_bytes)
        input_paths.append(input_path)
            
    output_filename = f"merged_{_id}.pdf"
    output_path = os.path.join(CONVERTED_DIR, output_filename)
    
    try:
        merge_pdfs(input_paths, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Birleştirme sırasında hata: {str(e)}")
        
    # Cleanup task
    files_to_delete = input_paths + [output_path]
    background_tasks.add_task(delete_files_after_delay, files_to_delete, 600)
    
    return JSONResponse(content={
        "message": "PDF'ler başarıyla birleştirildi!",
        "download_url": f"/download/{output_filename}",
        "original_filename": f"{len(files)} dosya birleştirildi",
        "converted_filename": "merged_file.pdf"
    })

@app.options("/split/")
@app.post("/split/")
async def split_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları bölünebilir.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Dosya boyutu 20MB sınırını aşıyor.")
        
    # Validate with magic
    mime_type = validate_file_type(file_bytes)
    if 'pdf' not in mime_type.lower():
        raise HTTPException(status_code=400, detail="Geçerli bir PDF dosyası değil.")
        
    _id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    input_path = os.path.join(UPLOAD_DIR, f"{_id}.pdf")
    temp_dir = os.path.join(CONVERTED_DIR, _id)
    os.makedirs(temp_dir, exist_ok=True)
    
    with open(input_path, "wb") as f:
        f.write(file_bytes)
        
    zip_filename = f"split_{_id}.zip"
    zip_filepath = os.path.join(CONVERTED_DIR, zip_filename)
    files_to_delete = [input_path, zip_filepath]
    
    try:
        split_files = split_pdf(input_path, temp_dir, base_name)
        
        # Zip them together
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in split_files:
                zipf.write(f, os.path.basename(f))
                files_to_delete.append(f)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bölme sırasında hata: {str(e)}")
        
    background_tasks.add_task(delete_files_after_delay, files_to_delete, 600)
    
    return JSONResponse(content={
        "message": "PDF başarıyla bölündü!",
        "download_url": f"/download/{zip_filename}",
        "original_filename": file.filename,
        "converted_filename": f"{base_name}_split.zip"
    })

@app.options("/compress/")
@app.post("/compress/")
async def compress_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), level: str = Form('medium')):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları sıkıştırılabilir.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE * 5: # allow 100MB for compression
        raise HTTPException(status_code=413, detail="Sıkıştırılacak dosya boyutu 100MB sınırını aşıyor.")
        
    # Validate with magic
    mime_type = validate_file_type(file_bytes)
    if 'pdf' not in mime_type.lower():
        raise HTTPException(status_code=400, detail="Geçerli bir PDF dosyası değil.")
        
    _id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    input_path = os.path.join(UPLOAD_DIR, f"{_id}_uncompressed.pdf")
    output_filename = f"{_id}_compressed.pdf"
    output_path = os.path.join(CONVERTED_DIR, output_filename)
    
    with open(input_path, "wb") as f:
        f.write(file_bytes)
        
    try:
        compress_pdf(input_path, output_path, level=level)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sıkıştırma sırasında hata: {str(e)}")
        
    background_tasks.add_task(delete_files_after_delay, [input_path, output_path], 600)
    
    return JSONResponse(content={
        "message": "PDF başarıyla sıkıştırıldı!",
        "download_url": f"/download/{output_filename}",
        "original_filename": file.filename,
        "converted_filename": f"{base_name}_compressed.pdf"
    })

@app.options("/rotate/")
@app.post("/rotate/")
async def rotate_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), degrees: int = Form(90)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları döndürülebilir.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Dosya boyutu 20MB sınırını aşıyor.")
        
    mime_type = validate_file_type(file_bytes)
    if 'pdf' not in mime_type.lower():
        raise HTTPException(status_code=400, detail="Geçerli bir PDF dosyası değil.")
        
    _id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    input_path = os.path.join(UPLOAD_DIR, f"{_id}_unrotated.pdf")
    output_filename = f"{_id}_rotated.pdf"
    output_path = os.path.join(CONVERTED_DIR, output_filename)
    
    with open(input_path, "wb") as f:
        f.write(file_bytes)
        
    try:
        rotate_pdf(input_path, output_path, degrees=degrees)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Döndürme sırasında hata: {str(e)}")
        
    background_tasks.add_task(delete_files_after_delay, [input_path, output_path], 600)
    
    return JSONResponse(content={
        "message": f"PDF başarıyla {degrees} derece döndürüldü!",
        "download_url": f"/download/{output_filename}",
        "original_filename": file.filename,
        "converted_filename": f"{base_name}_rotated.pdf"
    })

@app.options("/watermark/")
@app.post("/watermark/")
async def watermark_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), text: str = Form(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyalarına filigran eklenebilir.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Dosya boyutu 20MB sınırını aşıyor.")
        
    mime_type = validate_file_type(file_bytes)
    if 'pdf' not in mime_type.lower():
        raise HTTPException(status_code=400, detail="Geçerli bir PDF dosyası değil.")
        
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Filigran metni boş olamaz.")
        
    _id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    input_path = os.path.join(UPLOAD_DIR, f"{_id}_unwatermarked.pdf")
    output_filename = f"{_id}_watermarked.pdf"
    output_path = os.path.join(CONVERTED_DIR, output_filename)
    
    with open(input_path, "wb") as f:
        f.write(file_bytes)
        
    try:
        watermark_pdf(input_path, output_path, watermark_text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filigran eklenirken hata: {str(e)}")
        
    background_tasks.add_task(delete_files_after_delay, [input_path, output_path], 600)
    
    return JSONResponse(content={
        "message": "PDF'e başarıyla filigran eklendi!",
        "download_url": f"/download/{output_filename}",
        "original_filename": file.filename,
        "converted_filename": f"{base_name}_watermarked.pdf"
    })

@app.options("/pdf-to-image/")
@app.post("/pdf-to-image/")
async def pdf_to_image_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları görsellere dönüştürülebilir.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Dosya boyutu 20MB sınırını aşıyor.")
        
    mime_type = validate_file_type(file_bytes)
    if 'pdf' not in mime_type.lower():
        raise HTTPException(status_code=400, detail="Geçerli bir PDF dosyası değil.")
        
    _id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    input_path = os.path.join(UPLOAD_DIR, f"{_id}.pdf")
    temp_dir = os.path.join(CONVERTED_DIR, _id)
    os.makedirs(temp_dir, exist_ok=True)
    
    with open(input_path, "wb") as f:
        f.write(file_bytes)
        
    zip_filename = f"{base_name}_images_{_id}.zip"
    zip_filepath = os.path.join(CONVERTED_DIR, zip_filename)
    files_to_delete = [input_path, zip_filepath]
    
    try:
        image_files = pdf_to_images(input_path, temp_dir, base_name)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in image_files:
                zipf.write(f, os.path.basename(f))
                files_to_delete.append(f)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dönüştürme sırasında hata: {str(e)}")
        
    background_tasks.add_task(delete_files_after_delay, files_to_delete, 600)
    
    return JSONResponse(content={
        "message": "PDF başarıyla görsellere dönüştürüldü!",
        "download_url": f"/download/{zip_filename}",
        "original_filename": file.filename,
        "converted_filename": f"{base_name}_images.zip"
    })

@app.options("/protect/")
@app.post("/protect/")
async def protect_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), password: str = Form(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları şifrelenebilir.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Dosya boyutu 20MB sınırını aşıyor.")
        
    mime_type = validate_file_type(file_bytes)
    if 'pdf' not in mime_type.lower():
        raise HTTPException(status_code=400, detail="Geçerli bir PDF dosyası değil.")
        
    if not password:
        raise HTTPException(status_code=400, detail="Şifre boş olamaz.")
        
    _id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    input_path = os.path.join(UPLOAD_DIR, f"{_id}_unprotected.pdf")
    output_filename = f"{_id}_protected.pdf"
    output_path = os.path.join(CONVERTED_DIR, output_filename)
    
    with open(input_path, "wb") as f:
        f.write(file_bytes)
        
    try:
        encrypt_pdf(input_path, output_path, password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Şifreleme sırasında hata: {str(e)}")
        
    background_tasks.add_task(delete_files_after_delay, [input_path, output_path], 600)
    
    return JSONResponse(content={
        "message": "PDF başarıyla şifrelendi!",
        "download_url": f"/download/{output_filename}",
        "original_filename": file.filename,
        "converted_filename": f"{base_name}_protected.pdf"
    })

@app.options("/unlock/")
@app.post("/unlock/")
async def unlock_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), password: str = Form(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyalarının şifresi çözülebilir.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Dosya boyutu 20MB sınırını aşıyor.")
        
    mime_type = validate_file_type(file_bytes)
    if 'pdf' not in mime_type.lower():
        raise HTTPException(status_code=400, detail="Geçerli bir PDF dosyası değil.")
        
    if not password:
        raise HTTPException(status_code=400, detail="Şifre boş olamaz.")
        
    _id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    input_path = os.path.join(UPLOAD_DIR, f"{_id}_locked.pdf")
    output_filename = f"{_id}_unlocked.pdf"
    output_path = os.path.join(CONVERTED_DIR, output_filename)
    
    with open(input_path, "wb") as f:
        f.write(file_bytes)
        
    try:
        decrypt_pdf(input_path, output_path, password)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Şifre çözme sırasında hata: {str(e)}")
        
    background_tasks.add_task(delete_files_after_delay, [input_path, output_path], 600)
    
    return JSONResponse(content={
        "message": "PDF şifresi başarıyla çözüldü!",
        "download_url": f"/download/{output_filename}",
        "original_filename": file.filename,
        "converted_filename": f"{base_name}_unlocked.pdf"
    })

@app.options("/convert/jpg/")
@app.post("/convert/jpg/")
async def convert_to_jpg(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları JPG'ye dönüştürülebilir.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Dosya boyutu 20MB sınırını aşıyor.")
        
    mime_type = validate_file_type(file_bytes)
    if 'pdf' not in mime_type.lower():
        raise HTTPException(status_code=400, detail="Geçerli bir PDF dosyası değil.")
        
    _id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    input_path = os.path.join(UPLOAD_DIR, f"{_id}.pdf")
    temp_dir = os.path.join(CONVERTED_DIR, _id)
    os.makedirs(temp_dir, exist_ok=True)
    
    with open(input_path, "wb") as f:
        f.write(file_bytes)
        
    zip_filename = f"{base_name}_jpgs_{_id}.zip"
    zip_filepath = os.path.join(CONVERTED_DIR, zip_filename)
    files_to_delete = [input_path, zip_filepath]
    
    try:
        from scripts.converter_pdf2jpg import convert_pdf_to_jpg
        image_files = convert_pdf_to_jpg(input_path, temp_dir, base_name)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in image_files:
                zipf.write(f, os.path.basename(f))
                files_to_delete.append(f)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dönüştürme sırasında hata: {str(e)}")
        
    background_tasks.add_task(delete_files_after_delay, files_to_delete, 600)
    
    return JSONResponse(content={
        "message": "PDF başarıyla JPG görsellere dönüştürüldü!",
        "download_url": f"/download/{zip_filename}",
        "original_filename": file.filename,
        "converted_filename": f"{base_name}_jpgs.zip"
    })

@app.options("/convert/excel/")
@app.post("/convert/excel/")
async def convert_to_excel(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları Excel'e dönüştürülebilir.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Dosya boyutu 20MB sınırını aşıyor.")
        
    mime_type = validate_file_type(file_bytes)
    if 'pdf' not in mime_type.lower():
        raise HTTPException(status_code=400, detail="Geçerli bir PDF dosyası değil.")
        
    _id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    input_path = os.path.join(UPLOAD_DIR, f"{_id}_unconverted.pdf")
    output_filename = f"{_id}_converted.xlsx"
    output_path = os.path.join(CONVERTED_DIR, output_filename)
    
    with open(input_path, "wb") as f:
        f.write(file_bytes)
        
    try:
        import subprocess
        venv_python = os.path.join(os.getcwd(), "venv_excel", "Scripts", "python.exe")
        if not os.path.exists(venv_python):
            raise FileNotFoundError("venv_excel Python executable not found")
        
        cmd = [venv_python, "-c", "import sys; from scripts.converter_pdf2excel import convert_pdf_to_excel; convert_pdf_to_excel(sys.argv[1], sys.argv[2])", input_path, output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[HATA] PDF -> EXCEL dönüştürme başarısız. Geri dönüş kodu: {result.returncode}")
            print(f"[HATA] STDOUT: {result.stdout}")
            print(f"[HATA] STDERR: {result.stderr}")
            error_msg = result.stderr.strip() if result.stderr else 'Bilinmeyen Hata'
            raise RuntimeError(f"PDF'den Excel'e dönüştürme hatası (Kod {result.returncode}): {error_msg}")
            
    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=f"Dönüştürme sırasında hata: {str(e)}")
        
    background_tasks.add_task(delete_files_after_delay, [input_path, output_path], 600)
    
    return JSONResponse(content={
        "message": "PDF başarıyla Excel dosyasına dönüştürüldü!",
        "download_url": f"/download/{output_filename}",
        "original_filename": file.filename,
        "converted_filename": f"{base_name}.xlsx"
    })

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
