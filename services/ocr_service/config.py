"""
Конфигурация для OCR Service
"""

# Параметры OCR
OCR_CONFIDENCE_THRESHOLD = 0.6
OCR_LANGUAGE = "rus+eng"

# Параметры обработки изображений
IMAGE_DPI = 300
IMAGE_RESIZE_FACTOR = 1.5

# Поддерживаемые форматы файлов
SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]
SUPPORTED_PDF_FORMATS = [".pdf"]

# Максимальный размер файла (в байтах)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
