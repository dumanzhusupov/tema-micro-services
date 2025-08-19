#!/usr/bin/env python3
"""
Тест генерации задач с батчингом
"""

import os
import json
import requests
import time

# Конфигурация сервисов
TASK_GENERATOR_SERVICE = "http://localhost:8004"

# Пути к файлам
OUTPUT_DIR = "data/retrieved_jsonl"
RETRIEVED_TASKS_FILE = f"{OUTPUT_DIR}/algebra_6_1_retrieved_tasks.jsonl"
GENERATED_TASKS_FILE = f"{OUTPUT_DIR}/test_generated_tasks.jsonl"

def log_step(step_name, message):
    """Логирование этапов"""
    print(f"🔥 [{step_name}] {message}")

def test_task_generation(max_tasks: int = 10):
    """Тестирование генерации задач с батчингом"""
    log_step("TEST", f"Тестируем генерацию {max_tasks} задач с батчингом")
    
    # Создаем временный файл с ограниченным количеством задач
    temp_file = f"{OUTPUT_DIR}/temp_test_tasks.jsonl"
    with open(RETRIEVED_TASKS_FILE, 'r', encoding='utf-8') as infile:
        with open(temp_file, 'w', encoding='utf-8') as outfile:
            for i, line in enumerate(infile):
                if i >= max_tasks:
                    break
                outfile.write(line)
    
    log_step("TEST", f"Создан временный файл с {max_tasks} задачами: {temp_file}")
    
    start_time = time.time()
    response = requests.post(
        f"{TASK_GENERATOR_SERVICE}/generate-tasks-from-jsonl/",
        params={
            "jsonl_path": temp_file,
            "subject": "Математика"
        },
        timeout=600  # 10 минут таймаут для тестирования
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
    
    # Удаляем временный файл
    os.remove(temp_file)
    
    processing_time = end_time - start_time
    log_step("TEST", f"✅ Сгенерировано {len(generated_tasks)}/{max_tasks} задач за {processing_time:.2f} секунд")
    log_step("TEST", f"Результаты сохранены в {GENERATED_TASKS_FILE}")
    
    return generated_tasks

if __name__ == "__main__":
    try:
        print("\n🧪 ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ ЗАДАЧ С БАТЧИНГОМ")
        print("="*60)
        
        # Проверяем что файл с извлеченными задачами существует
        if not os.path.exists(RETRIEVED_TASKS_FILE):
            print(f"❌ Файл {RETRIEVED_TASKS_FILE} не найден!")
            exit(1)
        
        # Считаем количество задач в файле
        with open(RETRIEVED_TASKS_FILE, 'r') as f:
            total_tasks = sum(1 for line in f if line.strip())
        
        print(f"📋 Найдено {total_tasks} извлеченных задач")
        
        # Тестируем на маленьком наборе
        generated_tasks = test_task_generation(max_tasks=10)
        
        print(f"\n🎉 ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        print(f"✨ Успешно сгенерировано: {len(generated_tasks)} задач")
        
        # Показываем пример сгенерированной задачи
        if generated_tasks and len(generated_tasks) > 0:
            print(f"\n📝 Пример сгенерированной задачи:")
            example = generated_tasks[0]
            for key, value in example.items():
                print(f"   {key}: {str(value)[:100]}...")
                
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТЕ: {e}")
        raise
