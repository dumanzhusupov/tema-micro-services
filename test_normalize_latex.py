#!/usr/bin/env python3
"""
Тест функции normalize_latex_text для корректной обработки LaTeX и управляющих символов
"""

import requests
import json

# Тестовые данные с проблемными символами
test_chunks = [
    "Найти значение выражения: $\\frac{1}{2} + \\frac{1}{3}$\nОтвет записать в виде десятичной дроби.",
    "Решить уравнение: \\[ x^2 - 5x + 6 = 0 \\]\nИспользуя формулу дискриминанта.",
    "Вычислить: \\( \\sqrt{25} + \\sqrt{16} \\)\tОтвет:\f10"
]

test_toc = "Математика 6 класс\nАлгебра\nДроби\nУравнения"

# Отправляем тестовый запрос
request_data = {
    "chunks": test_chunks,
    "toc_text": test_toc,
    "output_jsonl_path": "data/retrieved_jsonl/test_normalize_latex.jsonl",
    "start_chunk": 0,
    "end_chunk": len(test_chunks)
}

print("🧪 Тестируем normalize_latex_text функцию...")
print(f"Исходные чанки:")
for i, chunk in enumerate(test_chunks):
    print(f"  {i+1}: {repr(chunk)}")

try:
    response = requests.post(
        "http://localhost:8001/process_chunks/",
        json=request_data,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Тест успешен! Обработано {len(result['results'])} задач")
        print(f"Результаты сохранены в: {result['jsonl_path']}")
        
        # Читаем и показываем результат
        with open("data/retrieved_jsonl/test_normalize_latex.jsonl", "r", encoding="utf-8") as f:
            print("\n📄 Содержимое файла:")
            for line_num, line in enumerate(f, 1):
                data = json.loads(line)
                print(f"\nЗапись {line_num}:")
                for key, value in data.items():
                    if isinstance(value, str):
                        print(f"  {key}: {repr(value)}")
                    else:
                        print(f"  {key}: {value}")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(f"Ответ: {response.text}")

except Exception as e:
    print(f"❌ Исключение: {e}")
