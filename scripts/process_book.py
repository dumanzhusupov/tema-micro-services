#!/usr/bin/env python3
"""
Скрипт для обработки учебника через полный пайплайн

Использование:
    python scripts/process_book.py <путь_к_файлу.md>
    python scripts/process_book.py <путь_к_файлу.md> --max-generate 20
    python scripts/process_book.py <путь_к_файлу.md> --output-dir data/results
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# Добавляем корневую директорию в PATH для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from tema import pipeline


def setup_logging(verbose: bool = False):
    """
    Настраивает логирование.
    
    Args:
        verbose: Если True, включает debug логи
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )


async def main():
    parser = argparse.ArgumentParser(
        description='Полный пайплайн обработки учебника: chunking -> retrieval -> generation'
    )
    parser.add_argument(
        'input_file',
        help='Путь к markdown файлу учебника'
    )
    parser.add_argument(
        '--output-dir',
        default='data/retrieved_jsonl',
        help='Директория для сохранения результатов (по умолчанию: data/retrieved_jsonl)'
    )
    parser.add_argument(
        '--max-generate',
        type=int,
        default=None,
        help='Максимальное количество задач для генерации (по умолчанию: все)'
    )
    parser.add_argument(
        '--start-chunk',
        type=int,
        default=0,
        help='Индекс начального чанка для обработки (по умолчанию: 0)'
    )
    parser.add_argument(
        '--end-chunk',
        type=int,
        default=None,
        help='Индекс конечного чанка (по умолчанию: до конца)'
    )
    parser.add_argument(
        '--no-generation',
        action='store_true',
        help='Пропустить этап генерации задач'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Включить подробное логирование'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Проверяем существование файла
    if not Path(args.input_file).exists():
        print(f"Ошибка: файл {args.input_file} не найден")
        sys.exit(1)
    
    try:
        if args.no_generation:
            # Пайплайн без генерации
            result = await pipeline.process_book_without_generation(
                input_file=args.input_file,
                output_dir=args.output_dir,
                start_chunk=args.start_chunk,
                end_chunk=args.end_chunk
            )
        else:
            # Полный пайплайн
            result = await pipeline.process_book(
                input_file=args.input_file,
                output_dir=args.output_dir,
                max_tasks_to_generate=args.max_generate,
                start_chunk=args.start_chunk,
                end_chunk=args.end_chunk
            )
        
        print("\nГотово!")
        print(f"Время выполнения: {result['total_time']:.2f}с")
        
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
    asyncio.run(main())

