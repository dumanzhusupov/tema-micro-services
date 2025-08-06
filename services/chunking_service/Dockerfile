FROM python:3.11-slim

WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код сервиса
COPY . .

# Открываем порт
EXPOSE 8002

# Запускаем сервис
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
