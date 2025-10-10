"""
Модуль для разбивки текста на чанки и извлечения оглавления

Основные функции:
- chunk_markdown: разбивает markdown текст на чанки по заголовкам
- extract_toc: извлекает оглавление из текста учебника
- beautify_toc: форматирует оглавление через OpenAI API
"""

import re
import logging
import tiktoken
import openai
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

import config

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def count_tokens(text: str, model: str = None) -> int:
    """
    Подсчитывает количество токенов в тексте для заданной модели.
    
    Args:
        text: Текст для подсчета токенов
        model: Модель OpenAI (по умолчанию из config)
        
    Returns:
        Количество токенов в тексте
    """
    model = model or config.DEFAULT_TOKENIZATION_MODEL
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


def chunk_markdown(text: str, warn_tokens: int = None, model: str = None) -> list[str]:
    """
    Разбивает markdown текст на чанки по заголовкам (строки начинающиеся с #).
    
    Args:
        text: Текст в формате markdown
        warn_tokens: Порог предупреждения о большом размере чанка (0 = без проверки)
        model: Модель для подсчета токенов
        
    Returns:
        Список чанков (строк текста)
    """
    warn_tokens = warn_tokens or config.DEFAULT_WARN_TOKENS
    model = model or config.DEFAULT_TOKENIZATION_MODEL
    
    # Разбиваем по заголовкам markdown (строки, начинающиеся с #)
    chunks = re.split(r"^#.*$", text, flags=re.MULTILINE)
    
    # Убираем пустые чанки и лишние пробелы
    chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    
    # Проверяем размер чанков
    max_tokens = 0
    for idx, chunk in enumerate(chunks):
        if warn_tokens > 0:
            tokens = count_tokens(chunk, model)
            max_tokens = max(max_tokens, tokens)
            
            if tokens > warn_tokens:
                logging.warning(
                    f"Chunk {idx+1} содержит {tokens} токенов, "
                    f"что превышает порог {warn_tokens}"
                )
    
    if warn_tokens > 0:
        logging.info(f"Максимальное число токенов в чанке: {max_tokens}")
    
    return chunks


def _find_toc_bounds(text: str) -> tuple[Optional[int], Optional[int]]:
    """
    Находит границы оглавления по стартовым и конечным паттернам.
    
    Args:
        text: Текст учебника
        
    Returns:
        Кортеж (start_idx, end_idx) или (None, None) если не найдено
    """
    # Ищем начало оглавления по одному из паттернов
    start_idx = None
    for pattern in config.TOC_START_PATTERNS:
        match = re.search(rf"(?mi)^(?:#{1,3}\s*)?\s*{pattern}\b", text)
        if match:
            start_idx = match.end()
            break
    
    if start_idx is None:
        return None, None
    
    # Ищем конец оглавления - ближайший из паттернов окончания
    end_candidates = []
    tail = text[start_idx:]
    
    for pattern in config.TOC_END_PATTERNS:
        match = re.search(rf"(?mi)^(?:#{1,3}\s*)?\s*{pattern}\b", tail)
        if match:
            end_candidates.append(start_idx + match.start())
    
    end_idx = min(end_candidates) if end_candidates else len(text)
    
    return start_idx, end_idx


def _cleanup_toc_block(block: str) -> str:
    """
    Очищает блок оглавления от мусора и форматирования.
    
    Удаляет:
    - Номера страниц (например ".... 12")
    - Ведущие номера разделов (например "1.2.3.")
    - Множественные пустые строки
    - Технические символы
    
    Args:
        block: Сырой текст оглавления
        
    Returns:
        Очищенный текст оглавления
    """
    lines = [line.rstrip() for line in block.splitlines()]
    cleaned = []
    
    for line in lines:
        stripped = line.strip()
        
        # Пропускаем пустые строки (но допускаем одну подряд)
        if not stripped:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        
        # Убираем номера страниц в конце строки (например ".... 12")
        stripped = re.sub(r"\.{2,}\s*\d+\s*$", "", stripped)
        
        # Убираем ведущие номера разделов (1., 1.2., А., и т.п.)
        stripped = re.sub(
            r"^(?:[A-Za-zА-Яа-яІіЇїЁё]\.|\d+(?:\.\d+)*\)|\d+(?:\.\d+)*\.?\s+)",
            "",
            stripped
        )
        
        # Пропускаем строки, которые являются только номерами страниц
        if re.fullmatch(r"\d{1,4}", stripped):
            continue
        
        # Пропускаем слишком короткие технические строки
        if len(stripped) < 2:
            continue
        
        cleaned.append(stripped)
    
    # Убираем ведущие и замыкающие пустые строки
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    
    return "\n".join(cleaned)


def _fallback_toc_scan(text: str) -> Optional[str]:
    """
    Запасной метод поиска оглавления путем сканирования начала/конца документа.
    
    Ищет блоки с характерными признаками оглавления:
    - Множественные строки с многоточиями и номерами страниц
    
    Args:
        text: Текст учебника
        
    Returns:
        Извлеченное оглавление или None
    """
    lines = text.splitlines()
    n = len(lines)
    
    # Сканируем первые и последние ~300 строк (примерно 10-15 страниц)
    window = 300
    candidates = [
        lines[:window],
        lines[max(0, n - window):]
    ]
    
    best = None
    
    for section in candidates:
        block = "\n".join(section)
        
        # Ищем признаки оглавления: строки с многоточиями и цифрами
        matches = re.findall(r"^.+\.{2,}\s*\d+\s*$", block, flags=re.MULTILINE)
        
        if len(matches) >= 5:
            # Выделяем плотный блок с такими строками
            start_line = None
            end_line = None
            
            for i, line in enumerate(section):
                if re.search(r"\.{2,}\s*\d+\s*$", line):
                    start_line = i
                    break
            
            for j in range(len(section) - 1, -1, -1):
                if re.search(r"\.{2,}\s*\d+\s*$", section[j]):
                    end_line = j
                    break
            
            if start_line is not None and end_line is not None and end_line > start_line:
                candidate = "\n".join(section[start_line:end_line + 1])
                if not best or len(candidate) > len(best):
                    best = candidate
    
    if best and len(best) >= config.TOC_MIN_LENGTH:
        return _cleanup_toc_block(best)
    
    return None


def extract_toc(text: str) -> Optional[str]:
    """
    Извлекает оглавление из текста учебника.
    
    Использует два подхода:
    1. Поиск по заголовкам (СОДЕРЖАНИЕ, Оглавление и т.д.)
    2. Fallback-сканирование начала/конца документа
    
    Args:
        text: Текст учебника
        
    Returns:
        Извлеченное и очищенное оглавление или None
    """
    # Попытка 1: Поиск по заголовкам
    start_idx, end_idx = _find_toc_bounds(text)
    
    if start_idx is not None and end_idx is not None and end_idx > start_idx:
        block = text[start_idx:end_idx].strip()
        cleaned = _cleanup_toc_block(block)
        
        if len(cleaned) >= config.TOC_MIN_LENGTH:
            return cleaned
    
    # Попытка 2: Fallback-сканирование
    return _fallback_toc_scan(text)


def _clean_gpt_output(raw: str) -> str:
    """
    Очищает ответ GPT от markdown code blocks.
    
    Args:
        raw: Сырой ответ от GPT
        
    Returns:
        Очищенный текст
    """
    if raw.lstrip().startswith("```"):
        raw = re.sub(r"```[a-zA-Z]*\s*", "", raw, flags=re.I).strip()
        raw = re.sub(r"```$", "", raw).strip()
    return raw


async def beautify_toc(toc_text: str) -> str:
    """
    Форматирует оглавление через OpenAI API для улучшения читаемости.
    
    Удаляет дубли, лишние символы, структурирует темы.
    
    Args:
        toc_text: Сырое оглавление
        
    Returns:
        Отформатированное оглавление
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY не найден в переменных окружения")
    
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    try:
        response = await client.chat.completions.create(
            model=config.CHUNKING_OPENAI_MODEL,
            temperature=config.CHUNKING_TEMPERATURE,
            top_p=config.CHUNKING_TOP_P,
            frequency_penalty=config.CHUNKING_FREQUENCY_PENALTY,
            presence_penalty=config.CHUNKING_PRESENCE_PENALTY,
            messages=[
                {"role": "system", "content": config.TOPICS_BEAUTIFY_PROMPT},
                {"role": "user", "content": f"Вот список тем из оглавления:\n\n{toc_text}"}
            ],
        )
        
        result = response.choices[0].message.content.strip()
        return _clean_gpt_output(result)
        
    except Exception as e:
        logging.error(f"Ошибка при форматировании оглавления через GPT: {e}")
        return f"Ошибка: {e}"


async def process_file(file_path: str, warn_tokens: int = 0, model: str = "gpt-3.5-turbo") -> tuple[list[str], Optional[str]]:
    """
    Полная обработка markdown файла: разбивка на чанки и извлечение оглавления.
    
    Args:
        file_path: Путь к markdown файлу
        warn_tokens: Порог предупреждения о размере чанка
        model: Модель для токенизации
        
    Returns:
        Кортеж (список чанков, отформатированное оглавление)
    """
    # Читаем файл
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Разбиваем на чанки
    chunks = chunk_markdown(text, warn_tokens=warn_tokens, model=model)
    
    # Извлекаем и форматируем оглавление
    toc = extract_toc(text)
    
    if toc:
        toc = await beautify_toc(toc)
    else:
        # Fallback оглавление по умолчанию
        toc = "Математика 6 класс, Алгебра, Геометрия, Арифметика"
    
    return chunks, toc

