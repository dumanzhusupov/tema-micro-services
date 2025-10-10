#!/usr/bin/env python3
"""
Скрипт для генерации новых задач из уже извлеченных

Использование:
    python scripts/generate_tasks.py <путь_к_jsonl> <выходной_файл>
    python scripts/generate_tasks.py data/retrieved_jsonl/algebra_6_1_retrieved_tasks.jsonl data/generated.jsonl
    python scripts/generate_tasks.py data/retrieved.jsonl data/generated.jsonl --max-tasks 10
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tema import pipeline


def setup_logging(verbose: bool = False):
    """Настраивает логирование."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )


async def main():
    parser = argparse.ArgumentParser(
        description='Генерация новых задач из извлеченных'
    )
    parser.add_argument(
        'input_file',
        help='Путь к JSONL файлу с извлеченными задачами'
    )
    parser.add_argument(
        'output_file',
        help='Путь для сохранения сгенерированных задач'
    )
    parser.add_argument(
        '--subject',
        default='Математика',
        help='Предмет (по умолчанию: Математика)'
    )
    parser.add_argument(
        '--max-tasks',
        type=int,
        default=None,
        help='Максимальное количество задач для генерации (по умолчанию: все)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Включить подробное логирование'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if not Path(args.input_file).exists():
        print(f"Ошибка: файл {args.input_file} не найден")
        sys.exit(1)
    
    try:
        result = await pipeline.generate_only(
            input_jsonl_path=args.input_file,
            output_jsonl_path=args.output_file,
            subject=args.subject,
            max_tasks=args.max_tasks
        )
        
        print("\nГотово!")
        print(f"Сгенерировано задач: {result['generated_tasks_count']}")
        print(f"Время выполнения: {result['total_time']:.2f}с")
        print(f"Результат сохранен в {result['output_file']}")
        
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

