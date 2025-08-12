#!/usr/bin/env python3
"""
Генерация всех задач батчами для обхода API limits
"""

import time
import subprocess
import sys

def run_generation_batch(start_task=0, batch_size=30, wait_time=60):
    """Генерируем батч задач с ожиданием между батчами"""
    
    # Модифицируем пайплайн для генерации батча
    with open('full_pipeline_algebra.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем параметры
    modified_content = content.replace(
        'step3_task_generation(max_tasks=0)',
        f'step3_task_generation_batch(start_task={start_task}, batch_size={batch_size})'
    )
    
    with open('temp_batch_pipeline.py', 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"🚀 Запуск батча: задачи {start_task}-{start_task+batch_size}")
    
    # Запускаем батч
    result = subprocess.run([sys.executable, 'temp_batch_pipeline.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Батч {start_task}-{start_task+batch_size} завершен успешно")
    else:
        print(f"❌ Ошибка в батче {start_task}-{start_task+batch_size}: {result.stderr}")
    
    if wait_time > 0:
        print(f"⏳ Ожидание {wait_time} секунд перед следующим батчем...")
        time.sleep(wait_time)

def main():
    total_tasks = 238
    batch_size = 30
    wait_time = 60  # 1 минута между батчами
    
    print(f"🎯 Генерируем {total_tasks} задач батчами по {batch_size}")
    
    for start_task in range(0, total_tasks, batch_size):
        remaining_tasks = min(batch_size, total_tasks - start_task)
        run_generation_batch(start_task, remaining_tasks, wait_time)
        
    print("🎉 Все батчи завершены!")

if __name__ == "__main__":
    main()
