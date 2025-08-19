import re
import logging
import tiktoken
import openai
import os
from dotenv import load_dotenv
from pathlib import Path
from config import (
    DEFAULT_MODEL_FOR_TOKENIZATION,
    DEFAULT_WARN_TOKENS, 
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_TOP_P,
    OPENAI_FREQUENCY_PENALTY,
    OPENAI_PRESENCE_PENALTY,
    TOPICS_PROMPT,
    TOC_START_PATTERNS,
    TOC_END_PATTERNS,
    TOC_MIN_LENGTH
)

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

def count_tokens(text: str, model: str = None) -> int:
    model = model or DEFAULT_MODEL_FOR_TOKENIZATION
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

def chunk_text(text: str, warn_tokens: int = None, model: str = None):
    warn_tokens = warn_tokens or DEFAULT_WARN_TOKENS
    model = model or DEFAULT_MODEL_FOR_TOKENIZATION
    # Разбиваем по заголовкам markdown (строки, начинающиеся с #)
    chunks = re.split(r"^#.*$", text, flags=re.MULTILINE)
    # Убираем пустые чанки и лишние пробелы
    chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    max_tokens = 0
    for idx, chunk in enumerate(chunks):
        tokens = count_tokens(chunk, model) if warn_tokens > 0 else None
        if tokens is not None:
            max_tokens = max(max_tokens, tokens)
        if tokens is not None and warn_tokens > 0 and tokens > warn_tokens:
            logging.warning(f"Chunk {idx+1} превышает {warn_tokens} токенов!")

    logging.info(f"Максимальное число токенов в чанке: {max_tokens}")
    return chunks

def _find_toc_bounds(text: str) -> tuple[int | None, int | None]:
    """Находит границы оглавления по стартовым и конечным паттернам."""
    # Старт: поддержка нескольких заголовков и без markdown-хэшей
    start_idx = None
    for pat in TOC_START_PATTERNS:
        m = re.search(rf"(?mi)^(?:#{1,3}\s*)?\s*{pat}\b", text)
        if m:
            start_idx = m.end()
            break

    if start_idx is None:
        return None, None

    # Конец: ищем ближайшее из заданных паттернов ниже старта
    end_candidates = []
    tail = text[start_idx:]
    for pat in TOC_END_PATTERNS:
        m = re.search(rf"(?mi)^(?:#{1,3}\s*)?\s*{pat}\b", tail)
        if m:
            end_candidates.append(start_idx + m.start())

    end_idx = min(end_candidates) if end_candidates else len(text)
    return start_idx, end_idx


def _cleanup_toc_block(block: str) -> str:
    """Чистит блок оглавления: убирает лишние пробелы, множественные пустые строки,
    обрезает явные номера страниц вида '.... 12' и отбрасывает мусорные строки."""
    lines = [l.rstrip() for l in block.splitlines()]
    cleaned = []
    for ln in lines:
        s = ln.strip()
        if not s:
            # допускаем одиночные пустые строки для визуальных блоков
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        # убираем концевые номера страниц в виде многоточий и цифр
        s = re.sub(r"\.{2,}\s*\d+\s*$", "", s)
        # убираем ведущие номера разделов (1., 1.2., А., т.п.)
        s = re.sub(r"^(?:[A-Za-zА-Яа-яІіЇїЁё]\.|\d+(?:\.\d+)*\)|\d+(?:\.\d+)*\.?\s+)", "", s)
        # отбрасываем строки, похожие на номера страниц
        if re.fullmatch(r"\d{1,4}", s):
            continue
        # слишком короткие технические хвосты пропускаем
        if len(s) < 2:
            continue
        cleaned.append(s)

    # убираем ведущие/замыкающие пустые строки
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned)


def _fallback_scan(text: str) -> str | None:
    """Запасной вариант: сканируем первые и последние страницы (по строкам)
    и пытаемся вытащить блок, похожий на оглавление."""
    lines = text.splitlines()
    n = len(lines)
    window = 300  # примерно 10-15 страниц при плотном тексте
    candidates = [lines[:window], lines[max(0, n - window):]]

    best = None
    for section in candidates:
        block = "\n".join(section)
        # ищем явные признаки содержания: множественные линии с многоточиями и цифрами
        matches = re.findall(r"^.+\.{2,}\s*\d+\s*$", block, flags=re.MULTILINE)
        if len(matches) >= 5:
            # выделяем максимально плотный подблок с такими линиями
            start_line = None
            end_line = None
            for i, ln in enumerate(section):
                if re.search(r"\.{2,}\s*\d+\s*$", ln):
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

    if best and len(best) >= TOC_MIN_LENGTH:
        return _cleanup_toc_block(best)
    return None


def extract_table_of_contents(text: str) -> str | None:
    # 1) Попытка по заголовкам
    start_idx, end_idx = _find_toc_bounds(text)
    if start_idx is not None and end_idx is not None and end_idx > start_idx:
        block = text[start_idx:end_idx].strip()
        cleaned = _cleanup_toc_block(block)
        if len(cleaned) >= TOC_MIN_LENGTH:
            return cleaned
    # 2) Фолбэк скан
    return _fallback_scan(text)

def clean_gpt_output_topics(raw: str) -> str:
    import re
    if raw.lstrip().startswith("```"):
        raw = re.sub(r"```[a-zA-Z]*\\s*", "", raw, flags=re.I).strip()
        raw = re.sub(r"```$", "", raw).strip()
    return raw

async def beautify_topics(topics_text: str) -> str:
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY не найден в .env")
    client = openai.AsyncOpenAI(api_key=OPENAI_KEY)
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=OPENAI_TEMPERATURE,
            top_p=OPENAI_TOP_P,
            frequency_penalty=OPENAI_FREQUENCY_PENALTY,
            presence_penalty=OPENAI_PRESENCE_PENALTY,
            messages=[
                {"role": "system", "content": TOPICS_PROMPT},
                {"role": "user", "content": f"Вот список тем из оглавления:\n\n{topics_text}"}
            ],
        )
        res = response.choices[0].message.content.strip()
        return clean_gpt_output_topics(res)
    except Exception as e:
        return f"Ошибка: {e}"
