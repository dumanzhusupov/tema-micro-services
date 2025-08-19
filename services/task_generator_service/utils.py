import json
import os
import re
import openai
from dotenv import load_dotenv
from models import TaskMessage
from datetime import datetime
from typing import Dict, Any, List
from config import OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_SEED, SYSTEM_PROMPT

def escape_controls(s: str) -> str:
    """Экранирует управляющие символы в строке"""
    m = {
        '\a': r'\a',
        '\b': r'\b',
        '\f': r'\f',
        '\n': r'\n',
        '\r': r'\r',
        '\t': r'\t',
        '\v': r'\v',
    }
    return s.translate({ord(k): v for k, v in m.items()})

def normalize_latex_text(text: str) -> str:
    """
    Нормализует LaTeX текст для JSONL:
    1. Экранирует управляющие символы
    2. Заменяет LaTeX-разделители математики на стандартные $$
    """
    if not isinstance(text, str):
        return text

    processed_text = escape_controls(text)
    # Display math: \[ ... \] -> $ ... $
    processed_text = re.sub(r'\\\[(.*?)\\\]', r'$\1$', processed_text, flags=re.DOTALL)
    # Inline math: \( ... \) -> $ ... $ (согласовано с retrieval_service)
    processed_text = re.sub(r'\\\((.*?)\\\)', r'$\1$', processed_text, flags=re.DOTALL)

    processed_text = re.sub(r'\$\$', r'$', processed_text, flags=re.DOTALL)

    return processed_text

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
# Use async client to match FastAPI async endpoints
client = openai.AsyncOpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

def clean_gpt_output(raw: str) -> str:
    import re
    print(f"🔍 До очистки: {repr(raw[:200])}")  # Логируем первые 200 символов
    
    # Убираем обёртку ```json ... ```
    if raw.lstrip().startswith("```"):
        raw = re.sub(r"```json\s*", "", raw, flags=re.I).strip()
        raw = re.sub(r"```\s*$", "", raw).strip()
    
    print(f"🧹 После очистки: {repr(raw[:200])}")  # Логируем результат
    return raw

async def generate_task_one(reference_task: Dict[str, Any], subject: str = "Алгебра", model: str = None, seed: int = None) -> Dict[str, Any]:
    # Используем значения из конфига если параметры не переданы
    model = model or OPENAI_MODEL
    #temperature = temperature or OPENAI_TEMPERATURE
    seed = seed or OPENAI_SEED
    
    user_prompt = (
        f"Предмет: {subject}. Вот пример задачи. Создай новую задачу с решением и ответом:\n\n"
        f"{reference_task}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    if client is None:
        raise RuntimeError("OPENAI_API_KEY is not set")
    # Enforce JSON output to avoid parsing errors
    resp = await client.chat.completions.create(
        model=model,
        #temperature=temperature,
        messages=messages,
        response_format={"type": "json_object"},
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
                data[k] = normalize_latex_text(v)
    except Exception as exc:
        print(f"❌ Ошибка парсинга JSON: {exc}")
        raise ValueError(f"Модель вернула невалидный JSON:\n{raw}") from exc
    return data

async def generate_tasks_from_jsonl(jsonl_path: str, subject: str = "Алгебра", model: str = None, seed: int = None) -> List[Dict[str, Any]]:
    # Используем значения из конфига если параметры не переданы
    model = model or OPENAI_MODEL
    #temperature = temperature or OPENAI_TEMPERATURE
    seed = seed or OPENAI_SEED
    
    tasks: List[Dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            ref_task = json.loads(line)
            new_task = await generate_task_one(ref_task, subject=subject, model=model, seed=seed)
            tasks.append(new_task)
    return tasks
