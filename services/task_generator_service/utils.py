import json
import os
import re
import openai
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
openai.api_key = OPENAI_KEY

def clean_gpt_output(raw: str) -> str:
    import re
    print(f"🔍 До очистки: {repr(raw[:200])}")  # Логируем первые 200 символов
    
    # Убираем обёртку ```json ... ```
    if raw.lstrip().startswith("```"):
        raw = re.sub(r"```json\s*", "", raw, flags=re.I).strip()
        raw = re.sub(r"```\s*$", "", raw).strip()
    
    print(f"🧹 После очистки: {repr(raw[:200])}")  # Логируем результат
    return raw

def generate_task_one(reference_task: Dict[str, Any], subject: str = "Алгебра", model: str = None, temperature: float = None, seed: int = None) -> Dict[str, Any]:
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
    resp = openai.ChatCompletion.create(
        model=model,
        temperature=temperature,
        seed=seed,
        messages=messages,
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

def generate_tasks_from_jsonl(jsonl_path: str, subject: str = "Алгебра", model: str = None, temperature: float = None, seed: int = None) -> List[Dict[str, Any]]:
    # Используем значения из конфига если параметры не переданы
    model = model or OPENAI_MODEL
    temperature = temperature or OPENAI_TEMPERATURE
    seed = seed or OPENAI_SEED
    
    tasks = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            ref_task = json.loads(line)
            new_task = generate_task_one(ref_task, subject=subject, model=model, temperature=temperature, seed=seed)
            tasks.append(new_task)
    return tasks
