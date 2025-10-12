"""
Модуль для извлечения математических задач из текстовых чанков

Использует OpenAI API для анализа текста и извлечения структурированных задач
с полями: id, original, solution, answer, topic, difficulty, tags, type.
"""

import os
import json
import re
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Any

import openai

import config

load_dotenv()

if "OPENAI_API_KEY" in os.environ:
    del os.environ["OPENAI_API_KEY"]

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def escape_control_chars(text: str) -> str:
    """
    Экранирует управляющие символы в строке для корректной записи в JSON.
    
    Args:
        text: Исходная строка
        
    Returns:
        Строка с экранированными управляющими символами
    """
    char_map = {
        '\a': r'\a',
        '\b': r'\b',
        '\f': r'\f',
        '\n': r'\n',
        '\r': r'\r',
        '\t': r'\t',
        '\v': r'\v',
    }
    return text.translate({ord(k): v for k, v in char_map.items()})


def normalize_latex(text: str) -> str:
    """
    Нормализует LaTeX разметку для единообразного формата.
    
    Преобразования:
    - \\[ ... \\] -> $ ... $ (display math)
    - \\( ... \\) -> $ ... $ (inline math)
    - $$ ... $$ -> $ ... $ (унификация)
    
    Args:
        text: Текст с LaTeX формулами
        
    Returns:
        Текст с нормализованной LaTeX разметкой
    """
    if not isinstance(text, str):
        return text
    
    # Экранируем управляющие символы
    processed = escape_control_chars(text)
    
    processed = re.sub(r'\\\\+', r'\\', processed)
    
    # Преобразуем display math: \\[ ... \\] -> $ ... $
    processed = re.sub(r'\\\[(.*?)\\\]', r'$\1$', processed, flags=re.DOTALL)
    
    # Преобразуем inline math: \\( ... \\) -> $ ... $
    processed = re.sub(r'\\\((.*?)\\\)', r'$\1$', processed, flags=re.DOTALL)
    
    # Унифицируем двойные доллары в одинарные
    processed = re.sub(r'\$\$', r'$', processed, flags=re.DOTALL)
    
    return processed


def _clean_gpt_output(raw: str) -> str:
    """
    Очищает ответ GPT от markdown code blocks.
    
    Args:
        raw: Сырой ответ от GPT
        
    Returns:
        Очищенный JSON текст
    """
    if raw.lstrip().startswith("```"):
        raw = re.sub(r"```json\s*", "", raw, flags=re.I).strip()
        raw = re.sub(r"```$", "", raw).strip()
    return raw


async def process_chunk(chunk_text: str, toc_text: str) -> Optional[str]:
    """
    Обрабатывает один текстовый чанк через OpenAI API для извлечения задач.
    
    Args:
        chunk_text: Текст чанка для анализа
        toc_text: Оглавление учебника (опционально, добавляется в prompt)
        
    Returns:
        JSON строка с извлеченными задачами или None при ошибке
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY не найден в переменных окружения")
    
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    # Формируем system prompt с учетом оглавления
    system_prompt = config.RETRIEVAL_SYSTEM_PROMPT
    if toc_text:
        system_prompt += f"\nВот список тем учебника (оглавление):\n{toc_text}\n\n"
    
    try:
        response = await client.chat.completions.create(
            model=config.RETRIEVAL_OPENAI_MODEL,
            frequency_penalty=config.RETRIEVAL_FREQUENCY_PENALTY,
            presence_penalty=config.RETRIEVAL_PRESENCE_PENALTY,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Вот фрагмент текста из учебника:\n\n{chunk_text}"}
            ],
        )
        
        result = response.choices[0].message.content.strip()
        return _clean_gpt_output(result)
        
    except Exception as e:
        logging.error(f"Ошибка при обработке чанка через OpenAI API: {e}")
        return None


async def extract_tasks_from_chunks(
    chunks: list[str],
    toc_text: Optional[str] = None,
    start_chunk: int = 0,
    end_chunk: Optional[int] = None
) -> list[dict[str, Any]]:
    """
    Извлекает задачи из списка чанков параллельно.
    
    Args:
        chunks: Список текстовых чанков
        toc_text: Оглавление учебника
        start_chunk: Индекс начального чанка
        end_chunk: Индекс конечного чанка (None = до конца)
        
    Returns:
        Список извлеченных задач (dict объектов)
    """
    if end_chunk is None:
        end_chunk = len(chunks)
    
    # Выбираем чанки для обработки
    selected_chunks = [
        (i, chunk_text) for i, chunk_text in enumerate(chunks)
        if start_chunk <= i < end_chunk
    ]
    
    logging.info(f"Обрабатываем {len(selected_chunks)} чанков параллельно...")
    
    # Создаем асинхронные задачи для всех чанков
    tasks = [
        process_chunk(chunk_text, toc_text)
        for i, chunk_text in selected_chunks
    ]
    
    # Выполняем все задачи параллельно
    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Собираем результаты
    results = []
    for (chunk_idx, chunk_text), gpt_response in zip(selected_chunks, chunk_results):
        # Обрабатываем исключения
        if isinstance(gpt_response, Exception):
            logging.error(f"Ошибка в chunk {chunk_idx}: {gpt_response}")
            continue
        
        # Пропускаем пустые ответы
        if not gpt_response or gpt_response == "[]":
            logging.debug(f"Chunk {chunk_idx}: задач не найдено")
            continue
        
        # Парсим JSON
        try:
            parsed = json.loads(gpt_response)
            
            if isinstance(parsed, list):
                # Нормализуем LaTeX в каждом элементе
                for task in parsed:
                    for key, value in task.items():
                        if isinstance(value, str):
                            task[key] = normalize_latex(value)
                    results.append(task)
            else:
                # Единичный объект
                for key, value in parsed.items():
                    if isinstance(value, str):
                        parsed[key] = normalize_latex(value)
                results.append(parsed)
            
            logging.info(f"Chunk {chunk_idx}: извлечено {len(parsed) if isinstance(parsed, list) else 1} задач")
            
        except json.JSONDecodeError as e:
            logging.error(f"Ошибка парсинга JSON в chunk {chunk_idx}: {e}")
            logging.debug(f"Ответ GPT: {gpt_response}")
    
    logging.info(f"Всего извлечено задач: {len(results)}")
    return results


async def extract_and_save_tasks(
    chunks: list[str],
    output_jsonl_path: str,
    toc_text: Optional[str] = None,
    start_chunk: int = 0,
    end_chunk: Optional[int] = None
) -> tuple[list[dict[str, Any]], str]:
    """
    Извлекает задачи из чанков и сохраняет в JSONL файл.
    
    Args:
        chunks: Список текстовых чанков
        output_jsonl_path: Путь для сохранения результата
        toc_text: Оглавление учебника
        start_chunk: Индекс начального чанка
        end_chunk: Индекс конечного чанка
        
    Returns:
        Кортеж (список задач, путь к файлу)
    """
    # Извлекаем задачи
    tasks = await extract_tasks_from_chunks(
        chunks=chunks,
        toc_text=toc_text,
        start_chunk=start_chunk,
        end_chunk=end_chunk
    )
    
    # Создаем директорию если не существует
    output_dir = os.path.dirname(output_jsonl_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Сохраняем в JSONL файл
    with open(output_jsonl_path, 'w', encoding='utf-8') as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    logging.info(f"Результаты сохранены в {output_jsonl_path}")
    
    return tasks, output_jsonl_path

