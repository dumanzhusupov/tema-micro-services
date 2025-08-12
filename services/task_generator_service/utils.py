import json
import os
import re
import openai
import asyncio
import aiofiles
import time
import logging
from dotenv import load_dotenv
from models import TaskMessage
from datetime import datetime
from typing import Dict, Any, List
from config import OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_SEED, SYSTEM_PROMPT

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def escape_controls(s: str) -> str:
    """
    Экранирует управляющие символы в литеральный вид
    \a,\b,\f,\n,\r,\t,\v → в строковый вид '\a','\b','\f','\n','\r','\t','\v'
    """
    control_chars = {
        '\a': r'\a',
        '\b': r'\b', 
        '\f': r'\f',
        '\n': r'\n',
        '\r': r'\r',
        '\t': r'\t',
        '\v': r'\v',
    }
    return s.translate({ord(k): v for k, v in control_chars.items()})

def normalize_latex_for_jsonl(text: str) -> str:
    """
    Нормализует LaTeX разметку для корректного хранения в JSONL.
    1. Экранирует управляющие символы (\f, \t, \n и т.д.)
    2. Заменяет LaTeX display math \\[ ... \\] -> $$ ... $$
    3. Заменяет LaTeX inline math \\( ... \\) -> $$ ... $$
    """
    if not isinstance(text, str):
        return text
    
    # Экранируем управляющие символы
    processed_text = escape_controls(text)
    
    # Заменяем display math: \\[ ... \\] -> $$ ... $$
    processed_text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', processed_text, flags=re.DOTALL)
    
    # Заменяем inline math: \\( ... \\) -> $$ ... $$
    processed_text = re.sub(r'\\\((.*?)\\\)', r'$$\1$$', processed_text, flags=re.DOTALL)

    return processed_text

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Асинхронный клиент OpenAI
client = openai.AsyncOpenAI(api_key=OPENAI_KEY)

def clean_gpt_output(raw: str) -> str:
    import re
    print(f"🔍 До очистки: {repr(raw[:200])}")  # Логируем первые 200 символов
    
    # Убираем обёртку ```json ... ```
    if raw.lstrip().startswith("```"):
        raw = re.sub(r"```json\s*", "", raw, flags=re.I).strip()
        raw = re.sub(r"```\s*$", "", raw).strip()
    
    print(f"🧹 После очистки: {repr(raw[:200])}")  # Логируем результат
    return raw

async def generate_task_one_with_retry(reference_task: Dict[str, Any], subject: str = "Алгебра", max_retries: int = 5) -> Dict[str, Any]:
    """
    Генерация задачи с retry логикой для обхода rate limits
    """
    for attempt in range(max_retries):
        try:
            return await generate_task_one(reference_task, subject)
        except openai.RateLimitError as e:
            wait_time = min(2 ** attempt * 10, 120)  # Увеличили задержку: от 10 до 120 сек
            logger.warning(f"Rate limit exceeded, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(wait_time)
            if attempt == max_retries - 1:
                logger.error(f"Failed to generate task after {max_retries} attempts: {e}")
                return {"error": f"Rate limit exceeded: {str(e)}"}
        except Exception as e:
            logger.error(f"Error generating task (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return {"error": f"Generation failed: {str(e)}"}
            await asyncio.sleep(1)
    
    return {"error": "Max retries exceeded"}

async def generate_task_one(reference_task: Dict[str, Any], subject: str = "Алгебра", model: str = None, temperature: float = None, seed: int = None) -> Dict[str, Any]:
    # Используем значения из конфига если параметры не переданы
    model = model or OPENAI_MODEL
    temperature = temperature or OPENAI_TEMPERATURE
    seed = seed or OPENAI_SEED
    
    user_prompt = (
        f"Предмет: {subject}. Вот пример задачи. Создай новую задачу с решением и ответом:\n\n"
        f"{reference_task}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    
    # Асинхронный вызов OpenAI API
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        seed=seed,
    )
    raw = resp.choices[0].message.content.strip()
    print(f"🤖 GPT ответ: {repr(raw)}")
    raw = clean_gpt_output(raw)
    # Сначала парсим JSON, потом экранируем LaTeX в данных
    try:
        data = json.loads(raw)
        print(f"✅ JSON распарсен успешно")
        # Обрабатываем строки в данных
        for k, v in data.items():
            if isinstance(v, str):
                data[k] = normalize_latex_for_jsonl(v)
    except Exception as exc:
        print(f"❌ Ошибка парсинга JSON: {exc}")
        raise ValueError(f"Модель вернула невалидный JSON:\n{raw}") from exc
    return data

async def generate_tasks_from_jsonl(jsonl_path: str, subject: str = "Алгебра", model: str = None, temperature: float = None, seed: int = None) -> List[Dict[str, Any]]:
    # Используем значения из конфига если параметры не переданы
    model = model or OPENAI_MODEL
    temperature = temperature or OPENAI_TEMPERATURE
    seed = seed or OPENAI_SEED
    
    # Асинхронно читаем файл
    async with aiofiles.open(jsonl_path, "r", encoding="utf-8") as f:
        lines = await f.readlines()
    
    # Парсим задачи
    reference_tasks = []
    for line in lines:
        if line.strip():
            reference_tasks.append(json.loads(line))
    
    print(f"🔄 Генерируем {len(reference_tasks)} задач с батчингом...")
    
    # Генерируем задачи батчами чтобы не превысить лимиты API
    batch_size = 3  # Уменьшили до 3 задач за раз для безопасности
    successful_tasks = []
    
    for i in range(0, len(reference_tasks), batch_size):
        batch = reference_tasks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(reference_tasks) + batch_size - 1) // batch_size
        
        print(f"📦 Обрабатываем батч {batch_num}/{total_batches} ({len(batch)} задач)")
        
        # Генерируем задачи в батче параллельно с retry
        batch_tasks = [
            generate_task_one_with_retry(ref_task, subject=subject)
            for ref_task in batch
        ]
        
        # Выполняем батч
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Обрабатываем результаты батча
        for j, result in enumerate(batch_results):
            task_num = i + j + 1
            if isinstance(result, Exception):
                logger.error(f"❌ Задача {task_num} не удалась: {result}")
            elif isinstance(result, dict) and "error" in result:
                logger.error(f"❌ Задача {task_num} не удалась: {result['error']}")
            else:
                successful_tasks.append(result)
                print(f"✅ Задача {task_num} сгенерирована")
        
        # Пауза между батчами для соблюдения лимитов
        if i + batch_size < len(reference_tasks):
            wait_time = 15  # Увеличили до 15 секунд между батчами
            print(f"⏱️ Пауза {wait_time}с между батчами для соблюдения лимитов API...")
            await asyncio.sleep(wait_time)
    
    print(f"🎉 Генерация завершена: {len(successful_tasks)}/{len(reference_tasks)} задач успешно")
    return successful_tasks
