#!/usr/bin/env python3
"""
End-to-End тест всего пайплайна микросервисов TEMA.

Тестирует цепочку:
1. Chunking Service - разбивка текста на чанки + извлечение оглавления
2. Retrieval Service - извлечение задач из чанков через GPT
3. Task Generator Service - генерация новых задач по образцам
"""

import requests
import json
import time
import os
from typing import Dict, List, Any

# Конфигурация сервисов
SERVICES = {
    "chunking": "http://localhost:8002",
    "retrieval": "http://localhost:8001", 
    "task_generator": "http://localhost:8004",
    "ocr": "http://localhost:8003"
}

def test_service_health(service_name: str, url: str) -> bool:
    """Проверяет доступность сервиса"""
    try:
        response = requests.get(f"{url}/docs", timeout=5)
        if response.status_code == 200:
            print(f"✅ {service_name.upper()} Service: OK")
            return True
        else:
            print(f"❌ {service_name.upper()} Service: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {service_name.upper()} Service: {e}")
        return False

def test_chunking_service() -> tuple[List[str], str, str]:
    """Тестирует Chunking Service с текстом из файла"""
    print("\n🔨 Тестируем Chunking Service...")
    
    # Читаем тестовый файл
    test_file_path = "data/books_md/algebra_6_1_sample.md"  # Возвращаемся к sample файлу для быстрого тестирования
    if not os.path.exists(test_file_path):
        print(f"❌ Тестовый файл не найден: {test_file_path}")
        return [], "", ""
    
    # Извлекаем имя книги из пути файла
    book_name = os.path.splitext(os.path.basename(test_file_path))[0]
    
    try:
        # Тестируем chunk endpoint
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test.md', f, 'text/markdown')}
            response = requests.post(
                f"{SERVICES['chunking']}/chunk/",
                files=files,
                params={'warn_tokens': 1000, 'model': 'gpt-3.5-turbo'}
            )
        
        if response.status_code == 200:
            chunk_data = response.json()
            chunks = chunk_data.get('chunks', [])
            print(f"✅ Chunking: Получено {len(chunks)} чанков")
            
            # Показываем первые 100 символов первого чанка
            if chunks:
                print(f"📝 Первый чанк (preview): {chunks[0][:100]}...")
        else:
            print(f"❌ Chunking failed: {response.status_code}")
            print(f"Response: {response.text}")
            return [], "", book_name
            
        # Тестируем extract_toc endpoint
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test.md', f, 'text/markdown')}
            response = requests.post(f"{SERVICES['chunking']}/extract_toc/", files=files)
        
        if response.status_code == 200:
            toc_data = response.json()
            toc = toc_data.get('toc', '')
            print(f"✅ TOC extraction: {len(toc) if toc else 0} символов")
            if toc:
                print(f"📚 TOC (preview): {toc[:200]}...")
                print(f"📚 Полное TOC: {toc}")  # Показываем полное оглавление для отладки
            else:
                print("⚠️ TOC пустое или не найдено")
            return chunks, toc, book_name
        else:
            print(f"❌ TOC extraction failed: {response.status_code}")
            print(f"Response: {response.text}")
            return chunks, "", book_name
            
    except Exception as e:
        print(f"❌ Chunking Service error: {e}")
        return [], "", ""

def test_retrieval_service(chunks: List[str], toc: str, book_name: str) -> List[Dict[str, Any]]:
    """Тестирует Retrieval Service"""
    print("\n🔍 Тестируем Retrieval Service...")
    
    if not chunks:
        print("❌ Нет чанков для обработки")
        return []
    
    try:
        # Используем только первые 3 чанка для быстрого тестирования
        test_chunks = chunks[:3]
        
        print(f"📚 Используем TOC для анализа: {'Да' if toc else 'Нет'}")
        if toc:
            print(f"📋 TOC содержимое: {toc[:100]}...")
        
        # Создаем имя файла для извлеченных задач
        retrieved_jsonl_path = f"data/retrieved_jsonl/{book_name}_retrieved_tasks.jsonl"
        
        request_data = {
            "chunks": test_chunks,
            "toc_text": toc or "",  # Если toc пустой, используем пустую строку
            "output_jsonl_path": retrieved_jsonl_path,
            "start_chunk": 0,
            "end_chunk": len(test_chunks)
        }
        
        response = requests.post(
            f"{SERVICES['retrieval']}/process_chunks/",
            json=request_data,
            timeout=60  # Увеличиваем timeout для GPT запросов
        )
        
        if response.status_code == 200:
            result = response.json()
            results = result.get('results', [])
            jsonl_path = result.get('jsonl_path', '')
            
            print(f"✅ Retrieval: Обработано {len(results)} результатов")
            print(f"📁 JSONL файл: {jsonl_path}")
            print(f"💾 Результаты сохранены в: {retrieved_jsonl_path}")
            
            # Показываем первую найденную задачу
            if results:
                first_task = results[0]
                print(f"📝 Первая задача: {first_task.get('original', 'N/A')[:100]}...")
            
            return results
        else:
            print(f"❌ Retrieval failed: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Retrieval Service error: {e}")
        return []

def test_task_generator_service(tasks: List[Dict[str, Any]], book_name: str) -> List[Dict[str, Any]]:
    """Тестирует Task Generator Service"""
    print("\n⚡ Тестируем Task Generator Service...")
    
    if not tasks:
        print("❌ Нет задач для генерации")
        return []
    
    try:
        # Берем максимум 3 валидные задачи для генерации
        valid_tasks = []
        for task in tasks:
            if isinstance(task, dict) and task.get('original'):
                valid_tasks.append(task)
                if len(valid_tasks) >= 3:  # Ограничиваем до 3 задач
                    break
        
        if not valid_tasks:
            print("❌ Не найдено валидных задач")
            return []
        
        print(f"🎯 Генерируем {len(valid_tasks)} задач...")
        generated_tasks = []
        
        # Генерируем задачи по одной
        for i, valid_task in enumerate(valid_tasks, 1):
            print(f"📝 Генерируем задачу {i}/{len(valid_tasks)}...")
            
            # Готовим запрос для генерации
            request_data = {
                "task_id": f"test-generated-task-{i}",
                "payload": valid_task,
                "created_at": "2025-08-05"
            }
            
            response = requests.post(
                f"{SERVICES['task_generator']}/generate-task/",
                json=request_data,
                params={'subject': 'Алгебра'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_task = result.get('generated_task', {})
                generated_tasks.append(generated_task)
                
                print(f"✅ Задача {i}: {generated_task.get('question', 'N/A')[:60]}...")
            else:
                print(f"❌ Ошибка генерации задачи {i}: {response.status_code}")
        
        if generated_tasks:
            # Сохраняем все сгенерированные задачи в JSONL файл
            generated_jsonl_path = f"data/retrieved_jsonl/{book_name}_generated_tasks.jsonl"
            save_generated_tasks_to_jsonl(generated_tasks, generated_jsonl_path)
            print(f"💾 Все {len(generated_tasks)} задач сохранены в: {generated_jsonl_path}")
            
            # Показываем итоговую статистику
            print(f"🎯 Итого сгенерировано: {len(generated_tasks)} задач")
            for i, task in enumerate(generated_tasks, 1):
                print(f"   {i}. {task.get('topic', 'N/A')} - {task.get('difficulty', 'N/A')}")
        
        return generated_tasks
            
    except Exception as e:
        print(f"❌ Task Generator Service error: {e}")
        return []

def save_generated_tasks_to_jsonl(tasks: List[Dict[str, Any]], file_path: str):
    """Сохраняет список сгенерированных задач в JSONL файл"""
    import os
    
    # Создаем директорию если не существует
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Перезаписываем файл (очищаем предыдущие результаты)
    with open(file_path, 'w', encoding='utf-8') as f:
        for task in tasks:
            json.dump(task, f, ensure_ascii=False)
            f.write('\n')

def main():
    """Основная функция для запуска всех тестов"""
    print("🚀 Запуск End-to-End тестирования пайплайна TEMA\n")
    
    # 1. Проверяем доступность всех сервисов
    print("1️⃣ Проверяем доступность сервисов...")
    all_services_ok = True
    for service_name, url in SERVICES.items():
        if not test_service_health(service_name, url):
            all_services_ok = False
    
    if not all_services_ok:
        print("\n❌ Не все сервисы доступны. Запустите их с помощью: docker-compose up")
        return
    
    # 2. Тестируем Chunking Service
    chunks, toc, book_name = test_chunking_service()
    if not chunks:
        print("\n❌ Тестирование остановлено - нет чанков")
        return
    
    print(f"\n📖 Обрабатываем книгу: {book_name}")
    
    # 3. Тестируем Retrieval Service  
    extracted_tasks = test_retrieval_service(chunks, toc, book_name)
    if not extracted_tasks:
        print("\n❌ Тестирование остановлено - не извлечены задачи")
        return
    
    # 4. Тестируем Task Generator Service
    generated_tasks = test_task_generator_service(extracted_tasks, book_name)
    
    # 5. Выводим итоги
    print("\n" + "="*60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print(f"� Книга: {book_name}")
    print(f"�📄 Обработано чанков: {len(chunks)}")
    print(f"📚 Извлечено оглавление: {'Да' if toc else 'Нет'}")
    print(f"🔍 Извлечено задач: {len(extracted_tasks)}")
    print(f"⚡ Сгенерировано новых задач: {len(generated_tasks)}")
    
    # Показываем пути к сохраненным файлам
    if extracted_tasks:
        print(f"📁 Извлеченные задачи: data/retrieved_jsonl/{book_name}_retrieved_tasks.jsonl")
    if generated_tasks:
        print(f"📁 Сгенерированные задачи: data/retrieved_jsonl/{book_name}_generated_tasks.jsonl")
    
    if generated_tasks:
        print("\n🎉 ПАЙПЛАЙН РАБОТАЕТ УСПЕШНО!")
    else:
        print("\n⚠️ Пайплайн завершен с ошибками")
    
    print("="*60)

if __name__ == "__main__":
    main()
