import json
import os
import re
import openai
import asyncio
import aiofiles
from dotenv import load_dotenv
from models import TaskMessage
from datetime import datetime
from typing import Dict, Any, List
from config import OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_SEED, SYSTEM_PROMPT

def process_jsonl(text: str) -> str:
    """
    Простая функция обработки строк для нормализации LaTeX в JSONL.
    Заменяет кастомные LaTeX-разделители и нормализует слеши.
    """
    if not isinstance(text, str):
        return text

    text = repr(text)
    # Работаем с ASCII кодами для обратного слеша (код 92)
    # Сначала схлопываем все последовательности слешей в один
    result = []
    i = 0
    while i < len(text):
        if text[i] == '\\':  # Обратный слеш
            # Пропускаем все последующие обратные слеши
            while i < len(text) and text[i] == '\\':
                i += 1
            # Добавляем двойной слеш
            result.append('\\')
        else:
            result.append(text[i])
            i += 1
    
    processed_text = ''.join(result)
    
    # Сначала заменяем display math: \\[ ... \\] -> $$ ... $$
    processed_text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', processed_text, flags=re.DOTALL)
    
    # Заменяем inline math: \\( ... \\) -> $ ... $
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
                data[k] = process_jsonl(v)
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
    
    print(f"🔄 Генерируем {len(reference_tasks)} задач параллельно...")
    
    # Параллельно генерируем задачи
    tasks = [
        generate_task_one(ref_task, subject=subject, model=model, temperature=temperature, seed=seed)
        for ref_task in reference_tasks
    ]
    
    # Выполняем все задачи параллельно
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Фильтруем успешные результаты
    successful_tasks = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ Задача {i+1} не удалась: {result}")
        else:
            successful_tasks.append(result)
            print(f"✅ Задача {i+1} сгенерирована")
    
    return successful_tasks
