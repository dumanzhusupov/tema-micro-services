#!/usr/bin/env python3
"""
Примеры использования библиотеки TEMA

Демонстрирует основные способы работы с библиотекой.
"""

import asyncio
import logging

from tema import pipeline, chunking, retrieval, generator

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)


async def example_full_pipeline():
    """
    Пример 1: Полный пайплайн обработки учебника
    """
    print("\n" + "=" * 60)
    print("ПРИМЕР 1: Полный пайплайн")
    print("=" * 60)
    
    result = await pipeline.process_book(
        input_file="data/books_md/algebra_6_1_sample.md",
        output_dir="data/retrieved_jsonl",
        max_tasks_to_generate=5  # Генерируем только 5 задач для примера
    )
    
    print(f"\nРезультаты:")
    print(f"  Чанков: {result['chunks_count']}")
    print(f"  Извлечено задач: {result['retrieved_tasks_count']}")
    print(f"  Сгенерировано задач: {result['generated_tasks_count']}")
    print(f"  Время: {result['total_time']:.2f}с")


async def example_without_generation():
    """
    Пример 2: Только извлечение задач без генерации
    """
    print("\n" + "=" * 60)
    print("ПРИМЕР 2: Только извлечение задач")
    print("=" * 60)
    
    result = await pipeline.process_book_without_generation(
        input_file="data/books_md/algebra_6_1_sample.md",
        output_dir="data/retrieved_jsonl"
    )
    
    print(f"\nРезультаты:")
    print(f"  Чанков: {result['chunks_count']}")
    print(f"  Извлечено задач: {result['retrieved_tasks_count']}")
    print(f"  Время: {result['total_time']:.2f}с")


async def example_modular():
    """
    Пример 3: Модульное использование - каждый этап отдельно
    """
    print("\n" + "=" * 60)
    print("ПРИМЕР 3: Модульное использование")
    print("=" * 60)
    
    # Этап 1: Chunking
    print("\nЭтап 1: Разбивка на чанки")
    chunks, toc = await chunking.process_file("data/books_md/algebra_6_1_sample.md")
    print(f"  Получено {len(chunks)} чанков")
    print(f"  Оглавление: {toc[:80]}..." if len(toc) > 80 else f"  Оглавление: {toc}")
    
    # Этап 2: Retrieval (только первые 3 чанка для примера)
    print("\nЭтап 2: Извлечение задач")
    tasks = await retrieval.extract_tasks_from_chunks(
        chunks=chunks[:3],  # Только первые 3 чанка
        toc_text=toc
    )
    print(f"  Извлечено {len(tasks)} задач из 3 чанков")
    
    # Этап 3: Generation (только первые 2 задачи)
    if tasks:
        print("\nЭтап 3: Генерация новых задач")
        new_tasks = await generator.generate_tasks_from_list(
            reference_tasks=tasks[:2],  # Только первые 2 задачи
            subject="Математика"
        )
        print(f"  Сгенерировано {len(new_tasks)} новых задач")
        
        # Выводим пример сгенерированной задачи
        if new_tasks:
            print("\n  Пример сгенерированной задачи:")
            task = new_tasks[0]
            print(f"    Тема: {task.get('topic', 'N/A')}")
            print(f"    Сложность: {task.get('difficulty', 'N/A')}")
            print(f"    Условие: {task.get('original', '')[:100]}...")


async def example_generation_only():
    """
    Пример 4: Только генерация из уже извлеченных задач
    """
    print("\n" + "=" * 60)
    print("ПРИМЕР 4: Генерация из готового JSONL файла")
    print("=" * 60)
    
    # Проверяем наличие файла
    import os
    input_file = "data/retrieved_jsonl/algebra_6_1_sample_generated_tasks.jsonl"
    
    if not os.path.exists(input_file):
        print(f"\nФайл {input_file} не найден. Пропускаем пример.")
        return
    
    result = await pipeline.generate_only(
        input_jsonl_path=input_file,
        output_jsonl_path="data/retrieved_jsonl/example_generated.jsonl",
        subject="Математика",
        max_tasks=3  # Генерируем только 3 задачи
    )
    
    print(f"\nРезультаты:")
    print(f"  Сгенерировано задач: {result['generated_tasks_count']}")
    print(f"  Время: {result['total_time']:.2f}с")


async def main():
    """
    Запускает все примеры
    """
    print("\nПРИМЕРЫ ИСПОЛЬЗОВАНИЯ БИБЛИОТЕКИ TEMA")
    print("=" * 60)
    
    # Раскомментируйте нужные примеры:
    
    # await example_full_pipeline()
    # await example_without_generation()
    await example_modular()
    # await example_generation_only()
    
    print("\n" + "=" * 60)
    print("ВСЕ ПРИМЕРЫ ЗАВЕРШЕНЫ")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

