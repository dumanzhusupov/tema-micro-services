# Changelog - Рефакторинг TEMA

## Версия 2.0.0 - Полный рефакторинг архитектуры

### Что изменилось

#### Убрано
- Удалена вся микросервисная архитектура (Docker, docker-compose, FastAPI)
- Удалены папка `services/` с 4 микросервисами
- Удалены Redis и RabbitMQ (не использовались)
- Удален `docker-compose.yml`
- Удален `Makefile`
- Удалены старые тестовые файлы:
  - `test_pipeline.py`
  - `test_generation.py`
  - `test_task_generation.py`
  - `batch_generation.py`
  - `debug_process_jsonl.py`
  - `full_pipeline_algebra.py`

#### Добавлено
- Новый пакет `tema/` с модульной структурой:
  - `tema/chunking.py` - разбивка текста на чанки
  - `tema/ocr.py` - OCR распознавание
  - `tema/retrieval.py` - извлечение задач
  - `tema/generator.py` - генерация задач
  - `tema/pipeline.py` - полный пайплайн

- Готовые скрипты в `scripts/`:
  - `process_book.py` - полный пайплайн обработки
  - `generate_tasks.py` - генерация задач
  - `ocr_pdf.py` - OCR для PDF
  - `ocr_image.py` - OCR для изображений

- Единый `config.py` с настройками и промптами
- Единый `requirements.txt` с минимальными зависимостями
- Новый `README.md` с полной документацией
- `QUICKSTART.md` - быстрый старт
- `.env.example` - пример конфигурации
- `example_usage.py` - примеры использования

### Технические улучшения

#### Архитектура
- Переход от микросервисов к простой библиотеке
- Нет HTTP overhead между компонентами
- Прямые вызовы функций вместо REST API
- Асинхронность сохранена для параллельной обработки

#### Код
- Чистый модульный код без эмодзи
- Подробные комментарии на русском
- Типизация для всех функций
- Единый стиль кода

#### Производительность
- Быстрее: нет сетевых запросов между модулями
- Меньше зависимостей
- Проще деплой: не нужен Docker

#### Использование
- Можно использовать как библиотеку в коде
- Можно запускать через готовые скрипты
- Можно импортировать в Jupyter notebooks
- Простая установка: `pip install -r requirements.txt`

### Миграция со старой версии

Старый код:
```bash
# Запуск сервисов
docker-compose up -d

# Запуск пайплайна
python full_pipeline_algebra.py
```

Новый код:
```bash
# Установка
pip install -r requirements.txt

# Запуск пайплайна
python scripts/process_book.py data/books_md/algebra_6_1.md
```

Или в Python:
```python
from tema import pipeline
result = await pipeline.process_book("data/books_md/algebra_6_1.md")
```

### Совместимость

- Формат данных остался прежним (JSONL)
- Все старые файлы данных совместимы
- Промпты и конфигурация сохранены
- Функционал не изменился, только упрощена архитектура

### Зависимости

Было: FastAPI, uvicorn, Redis, RabbitMQ, Docker и др.

Стало: openai, tiktoken, aiofiles, python-dotenv, httpx, requests, mpxpy

Сокращение зависимостей более чем в 3 раза.

