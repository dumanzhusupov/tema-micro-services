#!/usr/bin/env python3
"""
Скрипт для OCR распознавания PDF файлов через Mathpix

Использование:
    python scripts/ocr_pdf.py <путь_к_pdf>
    python scripts/ocr_pdf.py data/books_pdf/algebra_6_1.pdf
"""

import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tema import ocr


def setup_logging(verbose: bool = False):
    """Настраивает логирование."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )


def main():
    parser = argparse.ArgumentParser(
        description='OCR распознавание PDF файла через Mathpix'
    )
    parser.add_argument(
        'pdf_file',
        help='Путь к PDF файлу'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=450,
        help='Таймаут ожидания в секундах (по умолчанию: 450)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Включить подробное логирование'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    pdf_path = Path(args.pdf_file)
    
    if not pdf_path.exists():
        print(f"Ошибка: файл {pdf_path} не найден")
        sys.exit(1)
    
    if not ocr.validate_pdf_file(str(pdf_path)):
        print(f"Ошибка: файл должен быть в формате PDF")
        sys.exit(1)
    
    if not ocr.validate_file_size(str(pdf_path)):
        print(f"Ошибка: файл слишком большой (максимум 50 MB)")
        sys.exit(1)
    
    try:
        print(f"Начинаем распознавание PDF: {pdf_path}")
        print(f"Это может занять несколько минут...")
        
        result = ocr.ocr_pdf(str(pdf_path), timeout=args.timeout)
        
        print("\nГотово!")
        print(f"Результат сохранен в: {result['result_md_path']}")
        
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\nОшибка: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

