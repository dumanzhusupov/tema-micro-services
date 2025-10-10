# TEMA - Task Extraction and Math Assignment

Библиотека для обработки учебников математики: извлечение задач, генерация новых задач, OCR распознавание.

## Возможности

- **Chunking** - разбивка учебников на смысловые фрагменты
- **OCR** - распознавание текста из PDF и изображений через Mathpix
- **Retrieval** - извлечение математических задач через GPT
- **Generation** - генерация новых задач на основе извлеченных

## Установка

```bash
# Клонируйте репозиторий
git clone <repository>
cd tema-micro-services

# Установите зависимости
pip install -r requirements.txt

# Настройте переменные окружения
cp .env.example .env
# Отредактируйте .env и добавьте ваши API ключи
```

## Настройка

Создайте файл `.env` в корне проекта:

```env
# OpenAI API (обязательно для chunking, retrieval, generation)
OPENAI_API_KEY=your_openai_api_key

# Mathpix API (опционально, только для OCR)
MATHPIX_APP_ID=your_mathpix_app_id
MATHPIX_APP_KEY=your_mathpix_app_key
```

## Использование

### Через командную строку (скрипты)

#### Полный пайплайн обработки учебника

```bash
# Обработать весь учебник: chunking + retrieval + generation
python scripts/process_book.py data/books_md/algebra_6_1.md

# С ограничением генерации (только первые 20 задач)
python scripts/process_book.py data/books_md/algebra_6_1.md --max-generate 20

# Без генерации (только извлечение задач)
python scripts/process_book.py data/books_md/algebra_6_1.md --no-generation

# Указать выходную директорию
python scripts/process_book.py data/books_md/algebra_6_1.md --output-dir data/results
```

#### Генерация задач из уже извлеченных

```bash
# Сгенерировать новые задачи из существующего JSONL файла
python scripts/generate_tasks.py data/retrieved_jsonl/algebra_6_1_retrieved_tasks.jsonl data/generated.jsonl

# С ограничением количества
python scripts/generate_tasks.py data/retrieved.jsonl data/generated.jsonl --max-tasks 10
```

#### OCR распознавание

```bash
# Распознать PDF файл
python scripts/ocr_pdf.py data/books_pdf/algebra_6_1.pdf

# Распознать изображение
python scripts/ocr_image.py data/photos/page.png

# Сохранить результат в файл
python scripts/ocr_image.py data/photos/page.png --output result.md
```

### Через Python код (как библиотека)

#### Полный пайплайн

```python
import asyncio
from tema import pipeline

async def main():
    result = await pipeline.process_book(
        input_file="data/books_md/algebra_6_1.md",
        output_dir="data/results",
        max_tasks_to_generate=20  # None = без ограничений
    )
    
    print(f"Чанков: {result['chunks_count']}")
    print(f"Извлечено задач: {result['retrieved_tasks_count']}")
    print(f"Сгенерировано задач: {result['generated_tasks_count']}")

asyncio.run(main())
```

#### Только извлечение задач (без генерации)

```python
import asyncio
from tema import pipeline

async def main():
    result = await pipeline.process_book_without_generation(
        input_file="data/books_md/algebra_6_1.md",
        output_dir="data/results"
    )

asyncio.run(main())
```

#### Модульное использование

```python
import asyncio
from tema import chunking, retrieval, generator

async def main():
    # Шаг 1: Разбивка на чанки
    chunks, toc = await chunking.process_file("data/books_md/algebra_6_1.md")
    print(f"Получено {len(chunks)} чанков")
    
    # Шаг 2: Извлечение задач
    tasks = await retrieval.extract_tasks_from_chunks(chunks, toc)
    print(f"Извлечено {len(tasks)} задач")
    
    # Шаг 3: Генерация новых задач (из первых 5)
    new_tasks = await generator.generate_tasks_from_list(tasks[:5])
    print(f"Сгенерировано {len(new_tasks)} новых задач")

asyncio.run(main())
```

#### OCR

```python
from tema import ocr

# Распознать PDF
result = ocr.ocr_pdf("data/books_pdf/algebra.pdf")
print(f"Результат сохранен в {result['result_md_path']}")

# Распознать изображение
text = ocr.ocr_image_file("data/photos/page.png")
print(text)
```

## Структура проекта

```
tema-micro-services/
├── tema/                      # Основная библиотека
│   ├── __init__.py
│   ├── chunking.py           # Разбивка на чанки
│   ├── ocr.py                # OCR распознавание
│   ├── retrieval.py          # Извлечение задач
│   ├── generator.py          # Генерация задач
│   └── pipeline.py           # Полный пайплайн
│
├── scripts/                   # Готовые скрипты
│   ├── process_book.py       # Полный пайплайн
│   ├── generate_tasks.py     # Генерация задач
│   ├── ocr_pdf.py            # OCR для PDF
│   └── ocr_image.py          # OCR для изображений
│
├── data/                      # Данные
│   ├── books_md/             # Исходные markdown файлы
│   ├── books_pdf/            # PDF файлы
│   ├── photos/               # Изображения
│   └── retrieved_jsonl/      # Результаты обработки
│
├── experiments/               # Jupyter notebooks
│
├── config.py                  # Конфигурация (промпты, модели)
├── requirements.txt           # Зависимости
├── .env                      # API ключи (создать вручную)
└── README.md                 # Документация
```

## Конфигурация

Все настройки находятся в файле `config.py`:

- Модели OpenAI для каждого модуля
- Промпты для GPT
- Параметры токенизации
- Паттерны поиска оглавления
- Настройки OCR

Вы можете отредактировать этот файл для настройки поведения системы.

## Формат данных

### Извлеченные задачи (JSONL)

Каждая строка - JSON объект с полями:

```json
{
  "id": "123",
  "original": "Текст условия задачи",
  "solution": "Пошаговое решение",
  "answer": "Ответ",
  "topic": "Отношения и пропорции",
  "difficulty": "B",
  "tags": ["пропорции", "дроби", "уравнения"],
  "type": "Практическая"
}
```

### Сгенерированные задачи

Тот же формат, что и извлеченные задачи.

## Примеры

### Обработать главу учебника

```bash
python scripts/process_book.py data/books_md/algebra_6_1.md --max-generate 50
```

### Извлечь задачи без генерации

```bash
python scripts/process_book.py data/books_md/algebra_6_1.md --no-generation
```

### Сгенерировать больше задач из уже извлеченных

```bash
python scripts/generate_tasks.py \
    data/retrieved_jsonl/algebra_6_1_retrieved_tasks.jsonl \
    data/retrieved_jsonl/algebra_6_1_more_generated.jsonl \
    --max-tasks 100
```

### Распознать отсканированный учебник

```bash
# Сначала распознаем PDF
python scripts/ocr_pdf.py data/books_pdf/algebra_6_2.pdf

# Затем обрабатываем полученный markdown
python scripts/process_book.py data/books_pdf/algebra_6_2.md
```

## Технологии

- **Python 3.8+**
- **OpenAI GPT-4o / o4-mini** - анализ текста, извлечение и генерация задач
- **Mathpix** - OCR распознавание математических формул
- **tiktoken** - подсчет токенов
- **asyncio** - параллельная обработка чанков

## Логирование

Для включения подробных логов используйте флаг `--verbose`:

```bash
python scripts/process_book.py data/books_md/algebra_6_1.md --verbose
```

В Python коде:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Производительность

- **Chunking**: мгновенно (локально)
- **Retrieval**: зависит от количества чанков, ~2-5 сек на чанк (параллельно)
- **Generation**: ~3-7 сек на задачу (последовательно)
- **OCR**: PDF ~1-5 минут, изображение ~10-30 секунд

Для ускорения можно:
- Ограничить количество генерируемых задач (`--max-generate`)
- Обрабатывать только часть чанков (`--start-chunk`, `--end-chunk`)
- Пропустить генерацию (`--no-generation`)

## Лицензия

MIT

## Контакты

При возникновении вопросов создавайте Issues в репозитории.
