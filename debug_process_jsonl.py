#!/usr/bin/env python3
"""
Простой тест функции process_jsonl для отладки проблемы со слешами
"""

import re

def process_jsonl(text: str) -> str:
    """
    Простая функция обработки строк для нормализации LaTeX в JSONL.
    Заменяет кастомные LaTeX-разделители и нормализует слеши.
    """
    if not isinstance(text, str):
        return text

    print(f"🔍 Входящий текст: {repr(text)}")
    
    # Работаем с ASCII кодами для обратного слеша (код 92)
    # Сначала схлопываем все последовательности слешей в один
    result = []
    i = 0
    while i < len(text):
        if ord(text[i]) == 92:  # Обратный слеш
            # Пропускаем все последующие обратные слеши
            while i < len(text) and ord(text[i]) == 92:
                i += 1
            # Добавляем двойной слеш
            result.append('\\\\')  # Это 2 обратных слеша в коде Python
        else:
            result.append(text[i])
            i += 1
    
    processed_text = ''.join(result)
    print(f"🔧 После коллапса слешей: {repr(processed_text)}")
    
    # Сначала заменяем display math: \\[ ... \\] -> $$ ... $$
    processed_text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', processed_text, flags=re.DOTALL)
    
    # Заменяем inline math: \\( ... \\) -> $ ... $
    processed_text = re.sub(r'\\\((.*?)\\\)', r'$$\1$$', processed_text, flags=re.DOTALL)

    print(f"🎯 Итоговый результат: {repr(processed_text)}")
    return processed_text

# Тестируем разные случаи
test_cases = [
    "\\frac{3}{10}",
    "\\\\frac{3}{10}",
    "\\\\\\\\frac{3}{10}",
    "\\\\\\\\\\\\frac{3}{10}",
    "\\[x^2\\]",
    "\\\\[x^2\\\\]",
    "Normal text"
]

print("🧪 Тестирование функции process_jsonl")
print("=" * 50)

for i, test in enumerate(test_cases, 1):
    print(f"\n📋 Тест {i}:")
    result = process_jsonl(test)
    print(f"✅ Результат: {result}")
