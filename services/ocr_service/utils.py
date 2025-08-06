from mpxpy.mathpix_client import MathpixClient
import os
from dotenv import load_dotenv
import tempfile
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

mathpix_client = MathpixClient(
    app_id=os.getenv('APP_ID'),
    app_key=os.getenv('APP_KEY')
)

def ocr_image(image_bytes: bytes) -> str:
    # Сохраняем изображение во временный файл
    # Нужно проверить на способность принимать другие типы файлов [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    # Используем MathpixClient для обработки изображения
    image = mathpix_client.image_new(file_path=tmp_path)
    # Используем conversion для получения markdown (md)
    conversion = mathpix_client.conversion_new(
        mmd=image.mmd(),
        convert_to_md=True
    )
    conversion.wait_until_complete(timeout=30)
    md_text = conversion.to_md_text()
    return md_text

def process_pdf_with_mathpix(pdf_path: str) -> dict:
    pdf = mathpix_client.pdf_new(file_path=pdf_path)
    pdf.wait_until_complete(timeout=450)
    result_md_path = pdf_path.replace(".pdf", ".md")
    pdf.to_md_file(path=result_md_path)
    # Получаем количество страниц из metadata, если есть

    return {
        "status": "ok",
        "result_md_path": result_md_path,
    }
