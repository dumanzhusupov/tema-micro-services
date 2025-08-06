# TEMA Microservices 🚀

**TEMA** (Task Extraction and Math Assignment) - система микросервисов для извлечения и генерации математических задач из учебников.

## 🏗️ Архитектура

Система состоит из 4 микросервисов:

### 📚 **Chunking Service** (Port: 8001)
- Разбивает текст учебников на смысловые фрагменты
- Извлекает оглавление (TOC) из документов
- Обрабатывает Markdown файлы

### 🔍 **OCR Service** (Port: 8004) 
- Оптическое распознавание текста из изображений
- Поддержка PDF файлов и изображений
- Интеграция с Mathpix для математических формул

### 🎯 **Retrieval Service** (Port: 8002)
- Извлекает математические задачи из текстовых фрагментов
- Классифицирует задачи по темам и сложности
- Валидация и структурирование задач

### ⚡ **Task Generator Service** (Port: 8003)
- Генерирует новые математические задачи
- Использует OpenAI GPT для создания похожих задач
- Поддержка LaTeX форматирования

## 🚀 Быстрый старт

### Предварительные требования
- Docker и Docker Compose
- Python 3.11+ (для локального тестирования)

### 1. Клонирование и настройка
```bash
git clone <repository>
cd TEMA_micro_services

# Настройте .env файл с вашими API ключами
cp .env.example .env
# Отредактируйте .env файл
```

### 2. Запуск всех сервисов
```bash
# Собрать и запустить все сервисы
make build
make up

# Или через docker-compose напрямую
docker-compose up -d
```

### 3. Проверка работы
```bash
# Запустить end-to-end тест пайплайна
make test

# Или напрямую
python test_pipeline.py
```

## 📋 Доступные команды

```bash
make help          # Показать все доступные команды
make build         # Собрать Docker образы
make up            # Запустить все сервисы
make down          # Остановить сервисы
make logs          # Показать логи
make test          # Запустить тесты
make clean         # Очистить Docker
make status        # Статус сервисов
make restart       # Перезапустить сервисы
make dev           # Запуск с логами для разработки
```

## 🌐 Доступные endpoints

После запуска сервисы будут доступны по адресам:

- **Retrieval Service**: http://localhost:8001/docs
- **Chunking Service**: http://localhost:8002/docs  
- **OCR Service**: http://localhost:8003/docs
- **Task Generator Service**: http://localhost:8004/docs
- **RabbitMQ Management**: http://localhost:15672 (user/password)
- **Redis**: localhost:6379

## 🧪 Тестирование

### End-to-End тест
```bash
python test_pipeline.py
```

Тест проверяет весь пайплайн:
1. Разбивка текста на чанки (Chunking Service)
2. Извлечение задач из чанков (Retrieval Service)  
3. Генерация новых задач (Task Generator Service)

### Ручное тестирование
Используйте Swagger UI для тестирования отдельных endpoints:
- Откройте http://localhost:8001/docs для Retrieval Service
- Загрузите тестовые данные и выполните запросы

## 📁 Структура проекта

```
TEMA_micro_services/
├── services/                    # Микросервисы
│   ├── ocr_service/            # Распознавание текста
│   ├── chunking_service/       # Разбивка на чанки
│   ├── retrieval_service/      # Извлечение задач
│   └── task_generator_service/ # Генерация задач
├── data/                       # Тестовые данные
│   ├── books_md/              # Markdown файлы
│   ├── books_pdf/             # PDF файлы
│   └── retrieved_jsonl/       # Результаты обработки
├── experiments/               # Jupyter notebooks для экспериментов
├── docker-compose.yml        # Конфигурация Docker
├── test_pipeline.py          # End-to-end тесты
├── Makefile                  # Команды управления
└── README.md                 # Эта документация
```

## 🔧 Технологии

- **FastAPI** - веб-фреймворк для API
- **OpenAI GPT-4o-mini** - AI модель для обработки текста
- **Redis** - кэш и брокер сообщений
- **RabbitMQ** - очереди сообщений
- **Docker** - контейнеризация
- **Pydantic** - валидация данных
- **LaTeX** - форматирование математических формул

## 📊 Workflow

1. **OCR Service** извлекает текст из PDF/изображений
2. **Chunking Service** разбивает текст на удобные части и извлекает оглавление
3. **Retrieval Service** анализирует чанки через GPT и извлекает математические задачи
4. **Task Generator Service** создает новые задачи на основе найденных образцов

## 🐛 Отладка

### Просмотр логов
```bash
# Все сервисы
make logs

# Конкретный сервис
docker-compose logs -f retrieval_service
```

### Проверка статуса
```bash
make status
```

### Перезапуск проблемного сервиса
```bash
docker-compose restart task_generator_service
```

## 🔒 Переменные окружения

Настройте следующие переменные в `.env` файле:

```env
# OpenAI API для GPT сервисов
OPENAI_API_KEY=your_openai_key

# Mathpix API для OCR (опционально)
MATHPIX_APP_ID=your_mathpix_id
MATHPIX_APP_KEY=your_mathpix_key

# Подключения к сервисам
REDIS_URL=redis://redis:6379
RABBITMQ_URL=amqp://user:password@rabbitmq:5672/
```

## 📈 Мониторинг

- **RabbitMQ Management**: http://localhost:15672
- **Docker logs**: `make logs`
- **Health checks**: каждый сервис имеет `/docs` endpoint

## 🤝 Разработка

Для локальной разработки:

```bash
# Запуск отдельного сервиса
cd services/task_generator_service
python -m uvicorn main:app --reload --port 8004

# Или через Docker с привязкой volume
docker-compose up task_generator_service
```
