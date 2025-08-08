import os
import json
import re
import shutil

def process_text(text):
    """
    Нормализует текст, заменяя кастомные LaTeX-разделители и последовательности
    обратных слешей.
    """
    if not isinstance(text, str):
        return text

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
            result.append('\\\\')
        
        else:
            result.append(text[i])
            i += 1
    
    processed_text = ''.join(result)

    processed_text = processed_text.replace('$', ' $ ')

    processed_text = processed_text.replace('$  $', ' $$ ')

    # Сначала заменяем display math: \\[ ... \\] -> $$ ... $$
    processed_text = re.sub(r'\\\\\[(.*?)\\\\\]', r'$$\1$$', processed_text, flags=re.DOTALL)
    
    # Заменяем inline math: \\( ... \\) -> $ ... $
    processed_text = re.sub(r'\\\\\((.*?)\\\\\)', r'$$\1$$', processed_text, flags=re.DOTALL)


    return processed_text

def main():
    """
    Основная функция скрипта.
    """
    # Определяем пути к директориям
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(script_dir, 'data', 'retrieved_jsonl')
    target_dir = os.path.join(script_dir, 'data', 'corrected_jsonl')

    # Проверяем, существует ли исходная директория
    if not os.path.exists(source_dir):
        print(f"Ошибка: Исходная директория не найдена по пути: {source_dir}")
        return

    # Создаем целевую директорию, удаляя старую, если она есть
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)
    print(f"Создана целевая директория: {target_dir}")

    # Обрабатываем каждый .jsonl файл
    for filename in os.listdir(source_dir):
        if filename.endswith('.jsonl'):
            source_path = os.path.join(source_dir, filename)
            target_path = os.path.join(target_dir, filename)
            
            print(f"Обработка файла: {filename}...")
            
            try:
                with open(source_path, 'r', encoding='utf-8') as f_in:
                    content = f_in.read()

                # Просто пропускаем через process_text
                processed_content = process_text(content)
                
                # Записываем результат
                with open(target_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(processed_content)
                    
            except Exception as e:
                print(f"  - Произошла ошибка при обработке файла {filename}: {e}")

    print("\n✅ Обработка завершена. Исправленные файлы находятся в папке 'data/corrected_jsonl'.")

if __name__ == "__main__":
    main()
