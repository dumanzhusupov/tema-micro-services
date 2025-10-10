"""
Модуль для генерации новых математических задач на основе существующих

Использует OpenAI API для создания новых задач с измененными числами и формулировками,
сохраняя структуру и уровень сложности оригинальных задач.
"""

import os
import json
import re
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Optional

import openai

import config

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
        raw = re.sub(r"```\s*$", "", raw).strip()
    return raw


async def generate_task(
    reference_task: dict[str, Any],
    subject: str = "Алгебра",
    model: Optional[str] = None,
    seed: Optional[int] = None
) -> dict[str, Any]:
    """
    Генерирует новую задачу на основе образца.
    
    Args:
        reference_task: Образец задачи (dict с полями original, solution, answer и т.д.)
        subject: Предмет (Алгебра, Геометрия и т.д.)
        model: Модель OpenAI (по умолчанию из config)
        seed: Random seed для воспроизводимости
        
    Returns:
        Новая задача в виде dict
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY не найден в переменных окружения")
    
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    # Используем значения из конфига если не переданы
    model = model or config.GENERATOR_OPENAI_MODEL
    seed = seed or config.GENERATOR_SEED
    
    # Формируем prompt с примером задачи
    user_prompt = (
        f"Предмет: {subject}. Вот пример задачи. Создай новую задачу с решением и ответом:\n\n"
        f"{json.dumps(reference_task, ensure_ascii=False, indent=2)}"
    )
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": config.GENERATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},  # Принудительный JSON ответ
        )
        
        raw_response = response.choices[0].message.content.strip()
        cleaned = _clean_gpt_output(raw_response)
        
        # Парсим JSON
        try:
            data = json.loads(cleaned)
            
            # Нормализуем LaTeX во всех строковых полях
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = normalize_latex(value)
            
            return data
            
        except json.JSONDecodeError as e:
            logging.error(f"Ошибка парсинга JSON от GPT: {e}")
            logging.debug(f"Ответ GPT: {cleaned}")
            raise ValueError(f"Модель вернула невалидный JSON:\n{cleaned}") from e
        
    except Exception as e:
        logging.error(f"Ошибка при генерации задачи через OpenAI API: {e}")
        raise


async def generate_tasks_from_list(
    reference_tasks: list[dict[str, Any]],
    subject: str = "Математика",
    model: Optional[str] = None,
    seed: Optional[int] = None
) -> list[dict[str, Any]]:
    """
    Генерирует новые задачи из списка образцов.
    
    Args:
        reference_tasks: Список образцов задач
        subject: Предмет
        model: Модель OpenAI
        seed: Random seed
        
    Returns:
        Список новых задач
    """
    generated_tasks = []
    
    for idx, ref_task in enumerate(reference_tasks):
        logging.info(f"Генерация задачи {idx + 1}/{len(reference_tasks)}...")
        
        try:
            new_task = await generate_task(
                reference_task=ref_task,
                subject=subject,
                model=model,
                seed=seed
            )
            generated_tasks.append(new_task)
            
        except Exception as e:
            logging.error(f"Ошибка генерации задачи {idx + 1}: {e}")
            continue
    
    logging.info(f"Успешно сгенерировано {len(generated_tasks)} задач")
    return generated_tasks


async def generate_tasks_from_jsonl(
    jsonl_path: str,
    subject: str = "Математика",
    model: Optional[str] = None,
    seed: Optional[int] = None,
    max_tasks: Optional[int] = None
) -> list[dict[str, Any]]:
    """
    Генерирует новые задачи из JSONL файла с образцами.
    
    Args:
        jsonl_path: Путь к JSONL файлу с образцами
        subject: Предмет
        model: Модель OpenAI
        seed: Random seed
        max_tasks: Максимальное количество задач для генерации (None = все)
        
    Returns:
        Список новых задач
    """
    # Читаем образцы из файла
    reference_tasks = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            if max_tasks and idx >= max_tasks:
                break
            reference_tasks.append(json.loads(line))
    
    logging.info(f"Загружено {len(reference_tasks)} образцов из {jsonl_path}")
    
    # Генерируем задачи
    return await generate_tasks_from_list(
        reference_tasks=reference_tasks,
        subject=subject,
        model=model,
        seed=seed
    )


async def generate_and_save_tasks(
    input_jsonl_path: str,
    output_jsonl_path: str,
    subject: str = "Математика",
    max_tasks: Optional[int] = None
) -> tuple[list[dict[str, Any]], str]:
    """
    Генерирует новые задачи из файла и сохраняет результат.
    
    Args:
        input_jsonl_path: Путь к файлу с образцами
        output_jsonl_path: Путь для сохранения результата
        subject: Предмет
        max_tasks: Максимальное количество задач
        
    Returns:
        Кортеж (список задач, путь к файлу)
    """
    # Генерируем задачи
    tasks = await generate_tasks_from_jsonl(
        jsonl_path=input_jsonl_path,
        subject=subject,
        max_tasks=max_tasks
    )
    
    # Создаем директорию если не существует
    output_dir = os.path.dirname(output_jsonl_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Сохраняем в JSONL файл
    with open(output_jsonl_path, 'w', encoding='utf-8') as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    logging.info(f"Сгенерированные задачи сохранены в {output_jsonl_path}")
    
    return tasks, output_jsonl_path

