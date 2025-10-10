"""
TEMA - Task Extraction and Math Assignment

Библиотека для обработки учебников математики:
- Разбивка на чанки (chunking)
- OCR распознавание (ocr)
- Извлечение задач (retrieval)
- Генерация новых задач (generator)
"""

__version__ = "1.0.0"

from . import chunking
from . import ocr
from . import retrieval
from . import generator
from . import pipeline

__all__ = [
    "chunking",
    "ocr",
    "retrieval",
    "generator",
    "pipeline",
]

