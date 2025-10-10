#!/usr/bin/env python3
"""
Скрипт для OCR распознавания изображений через Mathpix

Использование:
    python scripts/ocr_image.py <путь_к_изображению>
    python scripts/ocr_image.py data/photos/algebra_6_1_22p.png
    python scripts/ocr_image.py photo.jpg --output result.md
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
        description='OCR распознавание изображения через Mathpix'
    )
    parser.add_argument(
        'image_file',
        help='Путь к файлу изображения'
    )
    parser.add_argument(
        '--output', '-o',
        help='Путь для сохранения результата (по умолчанию: в консоль)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Таймаут ожидания в секундах (по умолчанию: 30)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Включить подробное логирование'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    image_path = Path(args.image_file)
    
    if not image_path.exists():
        print(f"Ошибка: файл {image_path} не найден")
        sys.exit(1)
    
    if not ocr.validate_image_file(str(image_path)):
        print(f"Ошибка: неподдерживаемый формат изображения")
        print(f"Поддерживаемые форматы: .jpg, .jpeg, .png, .bmp, .tiff, .tif")
        sys.exit(1)
    
    if not ocr.validate_file_size(str(image_path)):
        print(f"Ошибка: файл слишком большой (максимум 50 MB)")
        sys.exit(1)
    
    try:
        print(f"Распознавание изображения: {image_path}")
        
        result_text = ocr.ocr_image_file(str(image_path), timeout=args.timeout)
        
        if args.output:
            # Сохраняем в файл
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result_text)
            
            print(f"\nРезультат сохранен в: {output_path}")
        else:
            # Выводим в консоль
            print("\nРезультат распознавания:")
            print("-" * 60)
            print(result_text)
            print("-" * 60)
        
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

