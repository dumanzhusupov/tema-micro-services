from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from utils import ocr_image, process_pdf_with_mathpix
from models import OCRResponse
from typing import List
import tempfile

load_dotenv()

app = FastAPI(title="Mathpix OCR API")

ALLOWED_IMAGE_EXTENSIONS: List[str] = [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]

@app.post("/ocr/", response_model=OCRResponse)
async def ocr_endpoint(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[-1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Требуется файл изображения: {ALLOWED_IMAGE_EXTENSIONS}")
    try:
        content = await file.read()
        text = ocr_image(content)
        return OCRResponse(text=text)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/ocr/pdf")
async def ocr_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Требуется PDF-файл")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name
    result = process_pdf_with_mathpix(temp_path)
    return JSONResponse(result)
