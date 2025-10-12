"""
Модуль полного пайплайна обработки учебников

Объединяет все этапы:
1. Chunking - разбивка на чанки и извлечение оглавления
2. Retrieval - извлечение задач из чанков
3. Generation - генерация новых задач

Предоставляет простой интерфейс для обработки книг одной командой.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional

from . import chunking
from . import retrieval
from . import generator


async def process_book(
    input_file: str,
    output_dir: str,
    toc : str,
    max_tasks_to_generate: Optional[int] = None,
    start_chunk: int = 0,
    end_chunk: Optional[int] = None
) -> dict:
    """
    Полный пайплайн обработки учебника: chunking -> retrieval -> generation.
    
    Этапы:
    1. Разбивает markdown файл на чанки
    2. Извлекает оглавление и форматирует его
    3. Извлекает математические задачи из чанков
    4. Генерирует новые задачи на основе извлеченных
    
    Args:
        input_file: Путь к markdown файлу учебника
        output_dir: Директория для сохранения результатов
        max_tasks_to_generate: Количество задач для генерации (None = все)
        start_chunk: Индекс начального чанка для обработки
        end_chunk: Индекс конечного чанка (None = до конца)
        
    Returns:
        Dict со статистикой:
        - input_file: путь к исходному файлу
        - chunks_count: количество чанков
        - retrieved_tasks_count: количество извлеченных задач
        - generated_tasks_count: количество сгенерированных задач
        - chunks_file: путь к файлу с чанками
        - retrieved_file: путь к файлу с извлеченными задачами
        - generated_file: путь к файлу со сгенерированными задачами
        - total_time: общее время выполнения в секундах
    """
    start_time = time.time()
    
    # Подготавливаем пути к выходным файлам
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = Path(input_file).stem
    chunks_file = os.path.join(output_dir, f"{base_name}_chunks.json")
    retrieved_file = os.path.join(output_dir, f"{base_name}_retrieved_tasks.jsonl")
    generated_file = os.path.join(output_dir, f"{base_name}_generated_tasks.jsonl")
    
    logging.info(f"Запуск полного пайплайна для {input_file}")
    logging.info("=" * 60)
    
    # Этап 1: Chunking
    logging.info("[ЭТАП 1/3] Chunking - разбивка на чанки и извлечение оглавления")
    chunks = await chunking.process_file(input_file)
    
    # Сохраняем результаты chunking
    chunks_data = {
        "source_file": input_file,
        "total_chunks": len(chunks),
        "chunks": chunks
    }
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    
    logging.info(f"Получено {len(chunks)} чанков")
    logging.info(f"Оглавление: {toc[:100]}..." if toc and len(toc) > 100 else f"Оглавление: {toc}")
    logging.info(f"Результаты сохранены в {chunks_file}")
    
    # Этап 2: Retrieval
    logging.info("\n[ЭТАП 2/3] Retrieval - извлечение задач из чанков")
    retrieval_start = time.time()
    
    tasks, _ = await retrieval.extract_and_save_tasks(
        chunks=chunks,
        output_jsonl_path=retrieved_file,
        toc_text=toc,
        start_chunk=start_chunk,
        end_chunk=end_chunk
    )
    
    retrieval_time = time.time() - retrieval_start
    logging.info(f"Извлечено {len(tasks)} задач за {retrieval_time:.2f} секунд")
    logging.info(f"Результаты сохранены в {retrieved_file}")
    
    # Этап 3: Generation
    logging.info("\n[ЭТАП 3/3] Generation - генерация новых задач")
    generation_start = time.time()
    
    # Если max_tasks_to_generate указан, ограничиваем количество
    if max_tasks_to_generate and max_tasks_to_generate > 0:
        logging.info(f"Ограничение: генерируем только для первых {max_tasks_to_generate} задач")
    
    generated_tasks, _ = await generator.generate_and_save_tasks(
        input_jsonl_path=retrieved_file,
        output_jsonl_path=generated_file,
        subject="Математика",
        max_tasks=max_tasks_to_generate
    )
    
    generation_time = time.time() - generation_start
    logging.info(f"Сгенерировано {len(generated_tasks)} задач за {generation_time:.2f} секунд")
    logging.info(f"Результаты сохранены в {generated_file}")
    
    # Итоговая статистика
    total_time = time.time() - start_time
    
    logging.info("\n" + "=" * 60)
    logging.info("ПАЙПЛАЙН ЗАВЕРШЕН")
    logging.info("=" * 60)
    logging.info(f"Исходный файл: {input_file}")
    logging.info(f"Чанков: {len(chunks)}")
    logging.info(f"Извлечено задач: {len(tasks)}")
    logging.info(f"Сгенерировано задач: {len(generated_tasks)}")
    logging.info(f"\nОбщее время выполнения: {total_time:.2f}с ({total_time/60:.2f} минут)")
    logging.info("=" * 60)
    
    return {
        "input_file": input_file,
        "chunks_count": len(chunks),
        "retrieved_tasks_count": len(tasks),
        "generated_tasks_count": len(generated_tasks),
        "chunks_file": chunks_file,
        "retrieved_file": retrieved_file,
        "generated_file": generated_file,
        "total_time": total_time,
        "retrieval_time": retrieval_time,
        "generation_time": generation_time
    }


async def process_book_without_generation(
    input_file: str,
    output_dir: str = "data/retrieved_jsonl",
    start_chunk: int = 0,
    end_chunk: Optional[int] = None
) -> dict:
    """
    Пайплайн без генерации: только chunking и retrieval.
    
    Полезно для быстрого извлечения задач без генерации новых.
    
    Args:
        input_file: Путь к markdown файлу учебника
        output_dir: Директория для сохранения результатов
        start_chunk: Индекс начального чанка
        end_chunk: Индекс конечного чанка
        
    Returns:
        Dict со статистикой
    """
    start_time = time.time()
    
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = Path(input_file).stem
    chunks_file = os.path.join(output_dir, f"{base_name}_chunks.json")
    retrieved_file = os.path.join(output_dir, f"{base_name}_retrieved_tasks.jsonl")
    
    logging.info(f"Запуск пайплайна (без генерации) для {input_file}")
    logging.info("=" * 60)
    
    # Этап 1: Chunking
    logging.info("[ЭТАП 1/2] Chunking")
    chunks, toc = await chunking.process_file(input_file)
    
    chunks_data = {
        "source_file": input_file,
        "total_chunks": len(chunks),
        "toc": toc,
        "chunks": chunks
    }
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    
    logging.info(f"Получено {len(chunks)} чанков")
    logging.info(f"Результаты сохранены в {chunks_file}")
    
    # Этап 2: Retrieval
    logging.info("\n[ЭТАП 2/2] Retrieval")
    tasks, _ = await retrieval.extract_and_save_tasks(
        chunks=chunks,
        output_jsonl_path=retrieved_file,
        toc_text=toc,
        start_chunk=start_chunk,
        end_chunk=end_chunk
    )
    
    logging.info(f"Извлечено {len(tasks)} задач")
    logging.info(f"Результаты сохранены в {retrieved_file}")
    
    total_time = time.time() - start_time
    
    logging.info("\n" + "=" * 60)
    logging.info("ПАЙПЛАЙН ЗАВЕРШЕН")
    logging.info("=" * 60)
    logging.info(f"Общее время: {total_time:.2f}с ({total_time/60:.2f} минут)")
    
    return {
        "input_file": input_file,
        "chunks_count": len(chunks),
        "retrieved_tasks_count": len(tasks),
        "chunks_file": chunks_file,
        "retrieved_file": retrieved_file,
        "total_time": total_time
    }


async def generate_only(
    input_jsonl_path: str,
    output_jsonl_path: str,
    subject: str = "Математика",
    max_tasks: Optional[int] = None
) -> dict:
    """
    Только генерация задач из уже извлеченных.
    
    Полезно если задачи уже извлечены и нужно только сгенерировать новые.
    
    Args:
        input_jsonl_path: Путь к JSONL файлу с извлеченными задачами
        output_jsonl_path: Путь для сохранения сгенерированных задач
        subject: Предмет
        max_tasks: Максимальное количество задач для генерации
        
    Returns:
        Dict со статистикой
    """
    start_time = time.time()
    
    logging.info(f"Генерация задач из {input_jsonl_path}")
    
    generated_tasks, _ = await generator.generate_and_save_tasks(
        input_jsonl_path=input_jsonl_path,
        output_jsonl_path=output_jsonl_path,
        subject=subject,
        max_tasks=max_tasks
    )
    
    total_time = time.time() - start_time
    
    logging.info(f"Сгенерировано {len(generated_tasks)} задач за {total_time:.2f}с")
    
    return {
        "input_file": input_jsonl_path,
        "generated_tasks_count": len(generated_tasks),
        "output_file": output_jsonl_path,
        "total_time": total_time
    }

