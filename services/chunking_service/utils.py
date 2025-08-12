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

def extract_table_of_contents(text: str) -> str | None:
    # Ищем "СОДЕРЖАНИЕ" капсом (может быть с ## в начале)
    start_match = re.search(r"#{0,3}\s*СОДЕРЖАНИЕ", text, re.IGNORECASE)
    if not start_match:
        return None
    start_idx = start_match.end()
    
    # Ищем конец содержания - может быть "Учебное издание", "Глоссарий", или конец файла
    end_idx = len(text)  # По умолчанию до конца файла
    
    for pattern in TOC_END_PATTERNS:
        end_match = re.search(pattern, text[start_idx:], re.IGNORECASE)
        if end_match:
            end_idx = start_idx + end_match.start()
            break
    
    toc_content = text[start_idx:end_idx].strip()
    # Если содержимое слишком короткое, возможно это не то что нужно
    if len(toc_content) < TOC_MIN_LENGTH:
        return None
    
    return toc_content

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
