# Быстрый старт TEMA

## Установка

```bash
# 1. Установите зависимости
pip install -r requirements.txt

# 2. Настройте API ключи
cp .env.example .env
# Отредактируйте .env и добавьте ваш OPENAI_API_KEY
```

## Примеры использования

### Обработать учебник полностью

```bash
python scripts/process_book.py data/books_md/algebra_6_1.md
```

### Обработать с ограничением генерации

```bash
python scripts/process_book.py data/books_md/algebra_6_1.md --max-generate 20
```

### Только извлечь задачи (без генерации)

```bash
python scripts/process_book.py data/books_md/algebra_6_1.md --no-generation
```

### Сгенерировать задачи из уже извлеченных

```bash
python scripts/generate_tasks.py \
    data/retrieved_jsonl/algebra_6_1_retrieved_tasks.jsonl \
    data/generated.jsonl \
    --max-tasks 10
```

### OCR - распознать PDF

```bash
python scripts/ocr_pdf.py data/books_pdf/algebra_6_1.pdf
```

### OCR - распознать изображение

```bash
python scripts/ocr_image.py data/photos/page.png --output result.md
```

## Использование как библиотека

```python
import asyncio
from tema import pipeline

async def main():
    result = await pipeline.process_book(
        input_file="data/books_md/algebra_6_1.md",
        max_tasks_to_generate=20
    )
    print(f"Извлечено: {result['retrieved_tasks_count']} задач")
    print(f"Сгенерировано: {result['generated_tasks_count']} задач")

asyncio.run(main())
```

## Структура результатов

Все результаты сохраняются в `data/retrieved_jsonl/`:

- `*_chunks.json` - разбитый на чанки текст
- `*_retrieved_tasks.jsonl` - извлеченные задачи
- `*_generated_tasks.jsonl` - сгенерированные задачи

Каждая строка JSONL файла - это одна задача с полями:
- `id` - номер задачи
- `original` - условие
- `solution` - решение
- `answer` - ответ
- `topic` - тема
- `difficulty` - сложность (A/B/C)
- `tags` - теги
- `type` - тип задачи

## Конфигурация

Все настройки в `config.py`:
- Модели GPT для каждого этапа
- Промпты для извлечения и генерации
- Параметры обработки

## Помощь

```bash
python scripts/process_book.py --help
python scripts/generate_tasks.py --help
python scripts/ocr_pdf.py --help
```

Полная документация в [README.md](README.md)

