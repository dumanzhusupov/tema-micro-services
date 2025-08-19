import os
import json
import re
import asyncio
import aiofiles
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

def escape_controls(s: str) -> str:
    """Экранирует управляющие символы в строке"""
    # \a,\b,\f,\n,\r,\t,\v → в литеральный вид
    m = {
        '\a': r'\a',
        '\b': r'\b',
        '\f': r'\f',
        '\n': r'\n',
        '\r': r'\r',
        '\t': r'\t',
        '\v': r'\v',
    }
    out = s.translate({ord(k): v for k, v in m.items()})
    return out

def normalize_latex_text(text: str) -> str:
    """
    Нормализует LaTeX текст для JSONL:
    1. Экранирует управляющие символы 
    2. Заменяет LaTeX-разделители математики на стандартные $$
    """
    if not isinstance(text, str):
        return text

    # Сначала экранируем управляющие символы
    processed_text = escape_controls(text)
    
    # Заменяем display math: \\[ ... \\] -> $ ... $
    processed_text = re.sub(r'\\\[(.*?)\\\]', r'$\1$', processed_text, flags=re.DOTALL)
    
    # Заменяем inline math: \\( ... \\) -> $ ... $
    processed_text = re.sub(r'\\\((.*?)\\\)', r'$\1$', processed_text, flags=re.DOTALL)

    processed_text = re.sub(r'\$\$', r'$', processed_text, flags=re.DOTALL)

    return processed_text

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Асинхронный клиент OpenAI
client = openai.AsyncOpenAI(api_key=OPENAI_KEY)

def clean_gpt_output(raw: str) -> str:
    if raw.lstrip().startswith("```"):
        raw = re.sub(r"```json\s*", "", raw, flags=re.I).strip()
        raw = re.sub(r"```$", "", raw).strip()
    return raw

async def process_chunk(chunk_text, toc_text: str):
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
        # Асинхронный вызов OpenAI API
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            #temperature=OPENAI_TEMPERATURE,
            #top_p=OPENAI_TOP_P,
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

async def process_jsonl_chunks(chunks: list[str], output_jsonl_path: str, toc_text: str, start_chunk=0, end_chunk=None):
    """
    Обрабатывает список чанков через GPT параллельно, добавляет список тем (toc_text) к SYSTEM_PROMPT,
    сохраняет результат в output_jsonl_path (jsonl), возвращает (list обработанных чанков, путь к созданному jsonl)
    """
    results = []
    if end_chunk is None:
        end_chunk = len(chunks)
    
    # Выбираем чанки для обработки
    selected_chunks = [
        (i, chunk_text) for i, chunk_text in enumerate(chunks)
        if start_chunk <= i < end_chunk
    ]
    
    print(f"\n🔄 Обрабатываем {len(selected_chunks)} чанков параллельно...")
    
    # Параллельно обрабатываем чанки
    tasks = [
        process_chunk(chunk_text, toc_text) 
        for i, chunk_text in selected_chunks
    ]
    
    # Выполняем все задачи параллельно
    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Ensure output directory exists
    out_dir = os.path.dirname(output_jsonl_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    # Асинхронно записываем результаты в файл
    async with aiofiles.open(output_jsonl_path, "w", encoding="utf-8") as outfile:
        for (chunk_idx, chunk_text), tagged_result in zip(selected_chunks, chunk_results):
            print(f"\n=== Результат chunk_{chunk_idx:03} ===")
            
            if isinstance(tagged_result, Exception):
                print(f"❌ Ошибка в chunk_{chunk_idx:03}: {tagged_result}")
                continue
                
            print(f"GPT raw response: {tagged_result}")
            if tagged_result and tagged_result != "[]":
                try:
                    parsed = json.loads(tagged_result)
                    print(f"✅ Успешно распарсено как JSON: {type(parsed)}")
                    if isinstance(parsed, list):
                        for elem in parsed:
                            results.append(elem)
                            # Обрабатываем строки в записи перед записью
                            processed_elem = {}
                            for k, v in elem.items():
                                processed_elem[k] = normalize_latex_text(v) if isinstance(v, str) else v
                            await outfile.write(json.dumps(processed_elem, ensure_ascii=False) + "\n")
                    else:
                        results.append(parsed)
                        # Обрабатываем строки в записи перед записью
                        processed_parsed = {}
                        for k, v in parsed.items():
                            processed_parsed[k] = normalize_latex_text(v) if isinstance(v, str) else v
                        await outfile.write(json.dumps(processed_parsed, ensure_ascii=False) + "\n")
                    print(f"✅ Сохранено chunk_{chunk_idx:03}")
                except Exception as e:
                    print(f"❌ Ошибка парсинга JSON chunk_{chunk_idx:03}: {e}")
                    print(f"Ответ: {tagged_result}")
            else:
                print(f"⏭️ Пропущен chunk_{chunk_idx:03}")
    
    print(f"\n🎉 Все загружено! Количество результатов: {len(results)}")
    print(f"📁 Файл сохранён по пути: {output_jsonl_path}")
    return results, output_jsonl_path


