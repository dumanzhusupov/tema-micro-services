import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
import openai
import httpx
from config import (
    OPENAI_MODEL, 
    OPENAI_TEMPERATURE, 
    OPENAI_TOP_P, 
    OPENAI_FREQUENCY_PENALTY, 
    OPENAI_PRESENCE_PENALTY,
    SYSTEM_PROMPT
)

def process_jsonl(text: str) -> str:
    """
    Простая функция обработки строк для нормализации LaTeX в JSONL.
    Заменяет кастомные LaTeX-разделители и нормализует слеши.
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
    
    # Сначала заменяем display math: \\[ ... \\] -> $$ ... $$
    processed_text = re.sub(r'\\\\\[(.*?)\\\\\]', r'$$\1$$', processed_text, flags=re.DOTALL)
    
    # Заменяем inline math: \\( ... \\) -> $ ... $
    processed_text = re.sub(r'\\\\\((.*?)\\\\\)', r'$$\1$$', processed_text, flags=re.DOTALL)

    return processed_text

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=OPENAI_KEY)

def clean_gpt_output(raw: str) -> str:
    if raw.lstrip().startswith("```"):
        raw = re.sub(r"```json\s*", "", raw, flags=re.I).strip()
        raw = re.sub(r"```$", "", raw).strip()
    return raw

def process_chunk(chunk_text, toc_text:str):
    """
    Обрабатывает один чанк через GPT, добавляя список тем (toc_text) к SYSTEM_PROMPT, если он передан.
    """
    prompt = SYSTEM_PROMPT
    if toc_text:
        prompt = prompt + f"\nВот список тем учебника (оглавление):\n{toc_text}\n\n"
    print("\n--- process_chunk LOG ---")
    print(f"Prompt (первые 300 символов): {prompt[:300]}")
    print(f"Chunk (первые 300 символов): {chunk_text[:300]}")
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=OPENAI_TEMPERATURE,
            top_p=OPENAI_TOP_P,
            frequency_penalty=OPENAI_FREQUENCY_PENALTY,
            presence_penalty=OPENAI_PRESENCE_PENALTY,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Вот фрагмент текста из учебника:\n\n{chunk_text}"}
            ],
        )
        print(f"OpenAI response object: {response}")
        res = response.choices[0].message.content.strip()
        print(f"OpenAI response content: {res}")
        return clean_gpt_output(res)
    except Exception as e:
        print(f"❌ Ошибка при обработке чанка: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_jsonl_chunks(chunks: list[str], output_jsonl_path: str, toc_text:str, start_chunk=0, end_chunk=None):
    """
    Обрабатывает список чанков через GPT, добавляет список тем (toc_text) к SYSTEM_PROMPT,
    сохраняет результат в output_jsonl_path (jsonl), возвращает (list обработанных чанков, путь к созданному jsonl)
    """
    results = []
    if end_chunk is None:
        end_chunk = len(chunks)
    with open(output_jsonl_path, "w", encoding="utf-8") as outfile:
        for i, chunk_text in enumerate(chunks):
            if i < start_chunk or i >= end_chunk:
                continue
            print(f"\n=== Обработка chunk_{i:03} ===")
            print(f"Исходный чанк (первые 300 символов): {chunk_text[:300]}")
            print(f"Длина чанка: {len(chunk_text)} символов")
            print(f"Переданный toc_text (первые 300 символов): {toc_text[:300] if toc_text else 'None'}")
            tagged_result = process_chunk(chunk_text, toc_text)
            print(f"GPT raw response: {tagged_result}")
            if tagged_result and tagged_result != "[]":
                try:
                    parsed = json.loads(tagged_result)
                    print(f"Успешно распарсено как JSON: {type(parsed)}")
                    if isinstance(parsed, list):
                        for elem in parsed:
                            results.append(elem)
                            # Обрабатываем строки в записи перед записью
                            processed_elem = {}
                            for k, v in elem.items():
                                processed_elem[k] = process_jsonl(v) if isinstance(v, str) else v
                            outfile.write(json.dumps(processed_elem, ensure_ascii=False) + "\n")
                    else:
                        results.append(parsed)
                        # Обрабатываем строки в записи перед записью
                        processed_parsed = {}
                        for k, v in parsed.items():
                            processed_parsed[k] = process_jsonl(v) if isinstance(v, str) else v
                        outfile.write(json.dumps(processed_parsed, ensure_ascii=False) + "\n")
                    print(f"Сохранено chunk_{i:03}")
                except Exception as e:
                    print(f"Ошибка парсинга JSON: {e}")
                    print(f"Ответ: {tagged_result}")
            else:
                print(f"Пропущен chunk_{i:03}")
    print(f"\nВсе загружено! Количество результатов: {len(results)}")
    print(f"Файл сохранён по пути: {output_jsonl_path}")
    return results, output_jsonl_path


