"""
Модуль для OCR распознавания текста из изображений и PDF файлов

Использует Mathpix API для распознавания математических формул и текста.
Поддерживает форматы: PNG, JPG, JPEG, BMP, TIFF, PDF.
"""

import os
import tempfile
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

from mpxpy.mathpix_client import MathpixClient

import config

load_dotenv()

# Инициализация Mathpix клиента
MATHPIX_APP_ID = os.getenv("MATHPIX_APP_ID")
MATHPIX_APP_KEY = os.getenv("MATHPIX_APP_KEY")

mathpix_client = None
if MATHPIX_APP_ID and MATHPIX_APP_KEY:
    mathpix_client = MathpixClient(
        app_id=MATHPIX_APP_ID,
        app_key=MATHPIX_APP_KEY
    )


def _ensure_mathpix_client():
    """
    Проверяет инициализацию Mathpix клиента.
    
    Raises:
        RuntimeError: Если API ключи не настроены
    """
    if mathpix_client is None:
        raise RuntimeError(
            "Mathpix API не настроен. "
            "Укажите MATHPIX_APP_ID и MATHPIX_APP_KEY в .env файле"
        )


def ocr_image(image_bytes: bytes, timeout: int = 30) -> str:
    """
    Распознает текст и формулы из изображения.
    
    Args:
        image_bytes: Байты изображения
        timeout: Таймаут ожидания результата в секундах
        
    Returns:
        Распознанный текст в формате markdown
        
    Raises:
        RuntimeError: Если Mathpix API не настроен
    """
    _ensure_mathpix_client()
    
    # Сохраняем изображение во временный файл
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    
    try:
        # Отправляем изображение в Mathpix
        image = mathpix_client.image_new(file_path=tmp_path)
        
        # Запускаем конвертацию в markdown
        conversion = mathpix_client.conversion_new(
            mmd=image.mmd(),
            convert_to_md=True
        )
        
        # Ожидаем завершения
        conversion.wait_until_complete(timeout=timeout)
        
        # Получаем результат
        md_text = conversion.to_md_text()
        
        logging.info(f"OCR завершен, получено {len(md_text)} символов")
        return md_text
        
    finally:
        # Удаляем временный файл
        try:
            os.unlink(tmp_path)
        except Exception as e:
            logging.warning(f"Не удалось удалить временный файл {tmp_path}: {e}")


def ocr_image_file(image_path: str, timeout: int = 30) -> str:
    """
    Распознает текст и формулы из файла изображения.
    
    Args:
        image_path: Путь к файлу изображения
        timeout: Таймаут ожидания результата в секундах
        
    Returns:
        Распознанный текст в формате markdown
    """
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    return ocr_image(image_bytes, timeout=timeout)


def ocr_pdf(pdf_path: str, timeout: int = 450) -> dict:
    """
    Распознает текст и формулы из PDF файла.
    
    Процесс:
    1. Отправка PDF в Mathpix
    2. Ожидание обработки (может занять несколько минут)
    3. Сохранение результата в markdown файл
    
    Args:
        pdf_path: Путь к PDF файлу
        timeout: Таймаут ожидания результата в секундах (по умолчанию 7.5 минут)
        
    Returns:
        Dict с полями:
        - status: 'ok' или 'error'
        - result_md_path: Путь к созданному markdown файлу
        - pages: Количество страниц (если доступно)
        
    Raises:
        RuntimeError: Если Mathpix API не настроен
    """
    _ensure_mathpix_client()
    
    logging.info(f"Начинаем OCR PDF файла: {pdf_path}")
    
    # Отправляем PDF в Mathpix
    pdf = mathpix_client.pdf_new(file_path=pdf_path)
    
    # Ожидаем завершения обработки
    logging.info(f"Ожидаем обработки (таймаут {timeout}с)...")
    pdf.wait_until_complete(timeout=timeout)
    
    # Формируем путь для результата
    result_md_path = pdf_path.replace(".pdf", ".md")
    
    # Сохраняем результат в markdown файл
    pdf.to_md_file(path=result_md_path)
    
    logging.info(f"OCR PDF завершен, результат сохранен в {result_md_path}")
    
    return {
        "status": "ok",
        "result_md_path": result_md_path,
    }


def validate_image_file(file_path: str) -> bool:
    """
    Проверяет, является ли файл поддерживаемым форматом изображения.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        True если формат поддерживается
    """
    ext = Path(file_path).suffix.lower()
    return ext in config.SUPPORTED_IMAGE_FORMATS


def validate_pdf_file(file_path: str) -> bool:
    """
    Проверяет, является ли файл PDF.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        True если файл PDF
    """
    ext = Path(file_path).suffix.lower()
    return ext in config.SUPPORTED_PDF_FORMATS


def validate_file_size(file_path: str, max_size: Optional[int] = None) -> bool:
    """
    Проверяет размер файла.
    
    Args:
        file_path: Путь к файлу
        max_size: Максимальный размер в байтах (по умолчанию из config)
        
    Returns:
        True если размер допустимый
    """
    max_size = max_size or config.MAX_FILE_SIZE
    file_size = os.path.getsize(file_path)
    return file_size <= max_size

