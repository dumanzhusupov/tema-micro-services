#!/usr/bin/env python3
"""
Полный пайплайн обработки algebra_6_1.md
1. Chunking - разбивка на чанки и извлечение оглавления
2. Retrieval - извлечение задач из чанков
3. Task Generation - генерация новых задач на основе найденных
"""

import os
import json
import requests
import time
from pathlib import Path

# Конфигурация сервисов
CHUNKING_SERVICE = "http://localhost:8002"
RETRIEVAL_SERVICE = "http://localhost:8001" 
TASK_GENERATOR_SERVICE = "http://localhost:8004"

# Пути к файлам
INPUT_FILE = "data/books_md/algebra_6_1.md"
OUTPUT_DIR = "data/retrieved_jsonl"
CHUNKS_FILE = f"{OUTPUT_DIR}/algebra_6_1_chunks.json"
RETRIEVED_TASKS_FILE = f"{OUTPUT_DIR}/algebra_6_1_retrieved_tasks.jsonl"
GENERATED_TASKS_FILE = f"{OUTPUT_DIR}/algebra_6_1_generated_tasks.jsonl"

def log_step(step_name, message):
    """Логирование этапов пайплайна"""
    print(f"🔥 [{step_name}] {message}")

def step1_chunking():
    """Этап 1: Разбивка на чанки и извлечение оглавления"""
    log_step("CHUNKING", f"Начинаем обработку файла: {INPUT_FILE}")
    
    # Читаем файл
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    log_step("CHUNKING", f"Файл прочитан, размер: {len(content)} символов")
    
    # Разбиваем на чанки - отправляем файл как multipart/form-data
    with open(INPUT_FILE, 'rb') as f:
        files = {'file': (INPUT_FILE, f, 'text/markdown')}
        response = requests.post(
            f"{CHUNKING_SERVICE}/chunk/",
            files=files,
            data={'warn_tokens': 0, 'model': 'gpt-3.5-turbo'}
        )
    
    if response.status_code != 200:
        raise Exception(f"Ошибка chunking: {response.text}")
    
    chunks_data = response.json()
    chunks = chunks_data["chunks"]
    
    log_step("CHUNKING", f"Получено {len(chunks)} чанков")
    
    # Извлекаем оглавление
    with open(INPUT_FILE, 'rb') as f:
        files = {'file': (INPUT_FILE, f, 'text/markdown')}
        toc_response = requests.post(
            f"{CHUNKING_SERVICE}/extract_toc/",
            files=files
        )
    
    if toc_response.status_code != 200:
        log_step("CHUNKING", f"Предупреждение: не удалось извлечь оглавление: {toc_response.text}")
        toc = "Математика 6 класс, Алгебра, Геометрия, Арифметика"
    else:
        toc_data = toc_response.json()
        toc = toc_data.get("toc", "Математика 6 класс")
    
    log_step("CHUNKING", f"Извлечено оглавление: {toc[:100]}...")
    
    # Сохраняем результаты
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    chunks_result = {
        "chunks": chunks,
        "toc": toc,
        "total_chunks": len(chunks),
        "source_file": INPUT_FILE
    }
    
    with open(CHUNKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(chunks_result, f, ensure_ascii=False, indent=2)
    
    log_step("CHUNKING", f"✅ Результаты сохранены в {CHUNKS_FILE}")
    return chunks, toc

def step2_retrieval(chunks, toc):
    """Этап 2: Извлечение задач из чанков"""
    log_step("RETRIEVAL", f"Начинаем извлечение задач из {len(chunks)} чанков")
    
    # Подготавливаем данные для retrieval service
    request_data = {
        "chunks": chunks,
        "toc_text": toc,
        "output_jsonl_path": RETRIEVED_TASKS_FILE,
        "start_chunk": 0,
        "end_chunk": len(chunks)
    }
    
    log_step("RETRIEVAL", "Отправляем запрос на retrieval service...")
    
    start_time = time.time()
    response = requests.post(
        f"{RETRIEVAL_SERVICE}/process_chunks/",
        json=request_data,
        timeout=1800  # 30 минут таймаут для большой книги
    )
    end_time = time.time()
    
    if response.status_code != 200:
        raise Exception(f"Ошибка retrieval: {response.text}")
    
    result = response.json()
    retrieved_tasks = result["results"]
    
    processing_time = end_time - start_time
    log_step("RETRIEVAL", f"✅ Извлечено {len(retrieved_tasks)} задач за {processing_time:.2f} секунд")
    log_step("RETRIEVAL", f"Результаты сохранены в {result['jsonl_path']}")
    
    return retrieved_tasks

def step3_task_generation(max_tasks: int = 20):
    """Этап 3: Генерация новых задач (с ограничением для тестирования)"""
    log_step("GENERATION", f"Начинаем генерацию задач на основе {RETRIEVED_TASKS_FILE}")
    
    # Ограничиваем количество задач для тестирования API limits
    if max_tasks and max_tasks > 0:
        # Создаем временный файл с ограниченным количеством задач
        temp_file = f"{OUTPUT_DIR}/temp_limited_tasks.jsonl"
        with open(RETRIEVED_TASKS_FILE, 'r', encoding='utf-8') as infile:
            with open(temp_file, 'w', encoding='utf-8') as outfile:
                for i, line in enumerate(infile):
                    if i >= max_tasks:
                        break
                    outfile.write(line)
        jsonl_path_to_use = temp_file
        log_step("GENERATION", f"Ограничиваем генерацию первыми {max_tasks} задачами")
    else:
        jsonl_path_to_use = RETRIEVED_TASKS_FILE
    
    start_time = time.time()
    response = requests.post(
        f"{TASK_GENERATOR_SERVICE}/generate-tasks-from-jsonl/",
        params={
            "jsonl_path": jsonl_path_to_use,
            "subject": "Математика"
        },
        timeout=1800  # 30 минут таймаут
    )
    end_time = time.time()
    
    if response.status_code != 200:
        raise Exception(f"Ошибка generation: {response.text}")
    
    result = response.json()
    generated_tasks = result["generated_tasks"]
    
    # Сохраняем сгенерированные задачи
    with open(GENERATED_TASKS_FILE, 'w', encoding='utf-8') as f:
        for task in generated_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    # Удаляем временный файл если использовался
    if max_tasks and max_tasks > 0:
        os.remove(temp_file)
    
    processing_time = end_time - start_time
    log_step("GENERATION", f"✅ Сгенерировано {len(generated_tasks)} новых задач за {processing_time:.2f} секунд")
    log_step("GENERATION", f"Результаты сохранены в {GENERATED_TASKS_FILE}")
    
    return generated_tasks

def print_summary(chunks, retrieved_tasks, generated_tasks):
    """Вывод итоговой сводки"""
    print("\n" + "="*60)
    print("🎉 ПАЙПЛАЙН ЗАВЕРШЕН УСПЕШНО!")
    print("="*60)
    print(f"📖 Исходный файл: {INPUT_FILE}")
    print(f"🧩 Количество чанков: {len(chunks)}")
    print(f"📋 Извлечено задач: {len(retrieved_tasks)}")
    print(f"✨ Сгенерировано задач: {len(generated_tasks)}")
    print("\n📁 Выходные файлы:")
    print(f"   • Чанки: {CHUNKS_FILE}")
    print(f"   • Извлеченные задачи: {RETRIEVED_TASKS_FILE}")
    print(f"   • Сгенерированные задачи: {GENERATED_TASKS_FILE}")
    print("="*60)

def main():
    """Главная функция пайплайна"""
    try:
        print("\n🚀 ЗАПУСК ПОЛНОГО ПАЙПЛАЙНА ОБРАБОТКИ ALGEBRA_6_1.MD")
        print("="*60)
        
        start_total_time = time.time()
        
        # Этап 1: Chunking
        chunks, toc = step1_chunking()
        
        # Этап 2: Retrieval
        retrieved_tasks = step2_retrieval(chunks, toc)
        
        # Этап 3: Task Generation (все задачи - осторожно с API limits!)
        generated_tasks = step3_task_generation(max_tasks=0)  # 0 = без ограничений
        
        end_total_time = time.time()
        total_time = end_total_time - start_total_time
        
        # Итоговая сводка
        print_summary(chunks, retrieved_tasks, generated_tasks)
        print(f"⏱️ Общее время выполнения: {total_time:.2f} секунд ({total_time/60:.2f} минут)")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ПАЙПЛАЙНЕ: {e}")
        raise

if __name__ == "__main__":
    main()
