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



async def process_file(file_path: str, warn_tokens: int = 0, model: str = "gpt-3.5-turbo") -> list[str]:
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
    
    return chunks

