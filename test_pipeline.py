#!/usr/bin/env python3
"""
End-to-End тест всего пайплайна микросервисов TEMA.
Улучшенная версия с кратким и информативным логированием.
"""

import requests
import json
import time
import os
import math
from typing import Dict, List, Any

# Конфигурация сервисов
SERVICES = {
    "chunking": "http://localhost:8002",
    "retrieval": "http://localhost:8001", 
    "task_generator": "http://localhost:8004",
    "ocr": "http://localhost:8003"
}

# Параметр батчинга для Retrieval (по умолчанию 10)
BATCH_SIZE = int(os.getenv("RETRIEVAL_BATCH_SIZE", "10"))

def test_service_health(service_name: str, url: str) -> bool:
    """Проверяет доступность сервиса"""
    try:
        response = requests.get(f"{url}/docs", timeout=5)
        if response.status_code == 200:
            print(f"✅ {service_name.capitalize()}: Ready")
            return True
        else:
            print(f"❌ {service_name.capitalize()}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {service_name.capitalize()}: Unavailable")
        return False

def test_chunking_service() -> tuple[List[str], str, str]:
    """Тестирует Chunking Service с текстом из файла"""
    print("🔨 Step 1: Processing document chunks...")
    
    # Читаем тестовый файл
    test_file_path = "data/books_md/algebra_6_1.md"
    if not os.path.exists(test_file_path):
        print(f"   ❌ File not found: {test_file_path}")
        return [], "", ""
    
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
            print(f"   ✅ Created {len(chunks)} text chunks")
        else:
            print(f"   ❌ Chunking failed: {response.status_code}")
            return [], "", book_name
            
        # Тестируем extract_toc endpoint
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test.md', f, 'text/markdown')}
            response = requests.post(f"{SERVICES['chunking']}/extract_toc/", files=files)
        
        if response.status_code == 200:
            toc_data = response.json()
            toc = toc_data.get('toc', '')
            if toc:
                print(f"   ✅ Extracted table of contents")
            else:
                print(f"   ⚠️ No table of contents found")
            return chunks, toc, book_name
        else:
            print(f"   ❌ TOC extraction failed: {response.status_code}")
            return chunks, "", book_name
            
    except Exception as e:
        print(f"   ❌ Chunking error: {str(e)[:50]}...")
        return [], "", ""

def test_retrieval_service(chunks: List[str], toc: str, book_name: str) -> List[Dict[str, Any]]:
    """Тестирует Retrieval Service"""
    print("🔍 Step 2: Extracting math problems...")
    
    if not chunks:
        print("   ❌ No chunks to process")
        return []
    
    try:
        # Limit processing to the first 50 chunks for test runs
        if len(chunks) > 50:
            print("   🔒 Limiting to first 50 chunks for test run")
            chunks = chunks[:50]

        total = len(chunks)
        batches = max(1, math.ceil(total / BATCH_SIZE))
        print(f"   📊 Processing {total} chunks in {batches} batches of {BATCH_SIZE} ({'with TOC' if toc else 'no TOC'})")

        combined_results: List[Dict[str, Any]] = []
        final_jsonl_path = "data/retrieved_jsonl/retrieved.jsonl"

        for b in range(batches):
            start = b * BATCH_SIZE
            end = min(start + BATCH_SIZE, total)
            batch_chunks = chunks[start:end]

            print(f"   ⏱️ Batch {b+1}/{batches}: chunks [{start}:{end})")

            request_data = {
                "chunks": batch_chunks,
                "toc_text": toc or "",
                # Do not persist per-batch files; combine in-memory and write once
                "start_chunk": 0,
                "end_chunk": len(batch_chunks)
            }

            response = requests.post(
                f"{SERVICES['retrieval']}/process_chunks/",
                json=request_data,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                results = result.get('results', [])
                combined_results.extend(results)
                print(f"      ✅ Found {len(results)} tasks in batch {b+1}")
            else:
                print(f"      ❌ Batch {b+1} failed: HTTP {response.status_code}")

        # Save only one consolidated JSONL
        if combined_results:
            save_extracted_tasks_to_jsonl(combined_results, final_jsonl_path)
            print(f"   ✅ Total found: {len(combined_results)} tasks")
            print(f"   💾 Saved JSONL to: {final_jsonl_path}")
        else:
            print("   ⚠️ No tasks found in any batch")

        return combined_results
        
    except Exception as e:
        print(f"   ❌ Retrieval error: {str(e)[:50]}...")
        return []

def test_task_generator_service(tasks: List[Dict[str, Any]], book_name: str) -> List[Dict[str, Any]]:
    """Тестирует Task Generator Service"""
    print("⚡ Step 3: Generating new tasks...")
    
    if not tasks:
        print("   ❌ No tasks to generate from")
        return []
    
    try:
        # Берем максимум 50 валидные задачи для генерации
        valid_tasks = []
        for task in tasks:
            if isinstance(task, dict) and task.get('original'):
                valid_tasks.append(task)
                if len(valid_tasks) >= 50:  # Ограничиваем количество задач для теста
                    break
        
        if not valid_tasks:
            print("   ❌ No valid tasks found")
            return []
        
        print(f"   🎯 Generating {len(valid_tasks)} new tasks...")
        generated_tasks = []
        
        # Генерируем задачи по одной
        for i, valid_task in enumerate(valid_tasks, 1):
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
                print(f"   ✅ Task {i}/{len(valid_tasks)} generated")
            else:
                print(f"   ❌ Task {i}/{len(valid_tasks)} failed")
        
        if generated_tasks:
            # Save all generated tasks into a single file
            generated_jsonl_path = "data/retrieved_jsonl/generated.jsonl"
            save_generated_tasks_to_jsonl(generated_tasks, generated_jsonl_path)
            print(f"   💾 Saved {len(generated_tasks)} tasks to: {generated_jsonl_path}")
        
        return generated_tasks
            
    except Exception as e:
        print(f"   ❌ Generation error: {str(e)[:50]}...")
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

def save_extracted_tasks_to_jsonl(results: List[Dict[str, Any]], file_path: str):
    """Сохраняет список извлечённых задач в JSONL файл"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in results:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')

def main():
    """Основная функция для запуска всех тестов"""
    print("🚀 TEMA Microservices Pipeline Test")
    print("=" * 50)
    
    # 1. Проверяем доступность всех сервисов
    print("🔧 Checking services health...")
    all_services_ok = True
    for service_name, url in SERVICES.items():
        if not test_service_health(service_name, url):
            all_services_ok = False
    
    if not all_services_ok:
        print("\n❌ Some services are unavailable. Run: docker-compose up")
        return
    
    print("")  # Пустая строка для разделения
    
    # 2. Тестируем Chunking Service
    chunks, toc, book_name = test_chunking_service()
    if not chunks:
        print("❌ Pipeline stopped: No chunks created")
        return
    
    # 3. Тестируем Retrieval Service  
    extracted_tasks = test_retrieval_service(chunks, toc, book_name)
    if not extracted_tasks:
        print("❌ Pipeline stopped: No tasks extracted")
        return
    
    # 4. Тестируем Task Generator Service
    generated_tasks = test_task_generator_service(extracted_tasks, book_name)
    
    # 5. Выводим итоги
    print("")
    print("=" * 50)
    print("📊 PIPELINE RESULTS")
    print("=" * 50)
    print(f"📖 Book: {book_name}")
    print(f"📄 Text chunks: {len(chunks)}")
    print(f"📚 Table of contents: {'Found' if toc else 'Not found'}")
    print(f"🔍 Extracted problems: {len(extracted_tasks)}")
    print(f"⚡ Generated problems: {len(generated_tasks)}")
    
    if extracted_tasks:
        print(f"📁 Extracted data: data/retrieved_jsonl/retrieved.jsonl")
    if generated_tasks:
        print(f"📁 Generated data: data/retrieved_jsonl/generated.jsonl")
    
    print("")
    if generated_tasks:
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    else:
        print("⚠️ Pipeline completed with issues")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
