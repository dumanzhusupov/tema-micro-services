#!/usr/bin/env python3
"""
Тест только для Task Generator Service.
Проверяет генерацию задач на основе существующих примеров.
"""

import requests
import json
import os
from typing import Dict, List, Any

# Конфигурация
TASK_GENERATOR_URL = "http://localhost:8004"

def test_service_health() -> bool:
    """Проверяет доступность Task Generator Service"""
    try:
        response = requests.get(f"{TASK_GENERATOR_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Task Generator Service: Ready")
            return True
        else:
            print(f"❌ Task Generator Service: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Task Generator Service: Unavailable ({str(e)[:50]}...)")
        return False

def load_sample_tasks(jsonl_file: str) -> List[Dict[str, Any]]:
    """Загружает примеры задач из JSONL файла"""
    tasks = []
    if not os.path.exists(jsonl_file):
        print(f"❌ Файл не найден: {jsonl_file}")
        return tasks
    
    try:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    task = json.loads(line)
                    if isinstance(task, dict) and task.get('original'):
                        tasks.append(task)
        print(f"📚 Загружено {len(tasks)} примеров задач из {jsonl_file}")
        return tasks
    except Exception as e:
        print(f"❌ Ошибка при загрузке задач: {str(e)[:50]}...")
        return []

def generate_single_task(reference_task: Dict[str, Any], task_num: int) -> Dict[str, Any]:
    """Генерирует одну задачу на основе примера"""
    try:
        print(f"   🎯 Генерация задачи {task_num}...")
        
        request_data = {
            "task_id": f"test-task-{task_num}",
            "payload": reference_task,
            "created_at": "2025-08-08"
        }
        
        response = requests.post(
            f"{TASK_GENERATOR_URL}/generate-task/",
            json=request_data,
            params={'subject': 'Алгебра'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_task = result.get('generated_task', {})
            print(f"   ✅ Задача {task_num} сгенерирована успешно")
            return generated_task
        else:
            print(f"   ❌ Задача {task_num} не удалась: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"      Детали ошибки: {error_detail}")
            except:
                print(f"      Ответ сервера: {response.text[:200]}...")
            return {}
            
    except Exception as e:
        print(f"   ❌ Ошибка генерации задачи {task_num}: {str(e)[:50]}...")
        return {}

def test_task_generation(sample_tasks: List[Dict[str, Any]], max_tasks: int = 5) -> List[Dict[str, Any]]:
    """Тестирует генерацию задач"""
    print(f"⚡ Тестирование генерации задач (максимум {max_tasks})...")
    
    if not sample_tasks:
        print("   ❌ Нет примеров для генерации")
        return []
    
    # Берем только валидные задачи
    valid_tasks = [task for task in sample_tasks if task.get('valid', True)]
    test_tasks = valid_tasks[:max_tasks]
    
    print(f"   📊 Будет сгенерировано {len(test_tasks)} задач")
    
    generated_tasks = []
    for i, reference_task in enumerate(test_tasks, 1):
        print(f"\n   📖 Исходная задача: {reference_task.get('original', 'Нет текста')[:80]}...")
        
        generated_task = generate_single_task(reference_task, i)
        if generated_task:
            generated_tasks.append(generated_task)
            
            # Показываем результат
            original_text = generated_task.get('original', 'Нет текста')
            print(f"   🎉 Сгенерированная задача: {original_text[:80]}...")
            if generated_task.get('answer'):
                print(f"   💡 Ответ: {generated_task['answer']}")
    
    return generated_tasks

def save_generated_tasks(tasks: List[Dict[str, Any]], output_file: str):
    """Сохраняет сгенерированные задачи в JSONL файл"""
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for task in tasks:
                json.dump(task, f, ensure_ascii=False)
                f.write('\n')
        
        print(f"💾 Сгенерированные задачи сохранены в: {output_file}")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {str(e)[:50]}...")

def show_generation_stats(generated_tasks: List[Dict[str, Any]]):
    """Показывает статистику генерации"""
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА ГЕНЕРАЦИИ ЗАДАЧ")
    print("="*60)
    
    if not generated_tasks:
        print("❌ Задачи не были сгенерированы")
        return
    
    print(f"✅ Всего сгенерировано задач: {len(generated_tasks)}")
    
    # Анализ полей
    fields = ['original', 'solution', 'answer', 'topic', 'type', 'difficulty']
    for field in fields:
        count = sum(1 for task in generated_tasks if task.get(field))
        print(f"   📋 {field}: {count}/{len(generated_tasks)} задач")
    
    # Показываем темы
    topics = {}
    for task in generated_tasks:
        topic = task.get('topic', 'Неизвестно')
        topics[topic] = topics.get(topic, 0) + 1
    
    print(f"\n📚 Распределение по темам:")
    for topic, count in topics.items():
        print(f"   • {topic}: {count}")
    
    # Показываем уровни сложности
    difficulties = {}
    for task in generated_tasks:
        difficulty = task.get('difficulty', 'Неизвестно')
        difficulties[difficulty] = difficulties.get(difficulty, 0) + 1
    
    print(f"\n🎯 Распределение по сложности:")
    for difficulty, count in difficulties.items():
        print(f"   • {difficulty}: {count}")

def main():
    """Основная функция теста"""
    print("🚀 Тест генерации задач Task Generator Service")
    print("="*60)
    
    # 1. Проверяем доступность сервиса
    if not test_service_health():
        print("\n❌ Task Generator Service недоступен. Запустите: docker-compose up")
        return
    
    # 2. Загружаем примеры задач
    sample_file = "data/retrieved_jsonl/retrieved.jsonl"
    sample_tasks = load_sample_tasks(sample_file)
    
    if not sample_tasks:
        print("\n❌ Не удалось загрузить примеры задач")
        print("💡 Сначала запустите: python test_pipeline.py")
        return
    
    # 3. Генерируем задачи
    generated_tasks = test_task_generation(sample_tasks, max_tasks=5)
    
    # 4. Сохраняем результаты
    if generated_tasks:
        output_file = "data/retrieved_jsonl/generated.jsonl"
        save_generated_tasks(generated_tasks, output_file)
    
    # 5. Показываем статистику
    show_generation_stats(generated_tasks)
    
    print("\n" + "="*60)
    if generated_tasks:
        print("🎉 ТЕСТ ГЕНЕРАЦИИ ЗАВЕРШЕН УСПЕШНО!")
    else:
        print("⚠️ Тест завершен, но задачи не были сгенерированы")
    print("="*60)

if __name__ == "__main__":
    main()
