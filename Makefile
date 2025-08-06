# TEMA Microservices Makefile

.PHONY: help build up down logs test clean

help: ## Показать справку
	@echo "TEMA Microservices - команды управления:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Собрать все Docker образы
	@echo "🔨 Сборка Docker образов..."
	docker-compose build

up: ## Запустить все сервисы
	@echo "🚀 Запуск всех сервисов..."
	docker-compose up -d
	@echo "✅ Сервисы запущены!"
	@echo "📖 Swagger UI доступен по адресам:"
	@echo "   - Retrieval Service:     http://localhost:8001/docs"
	@echo "   - Chunking Service:      http://localhost:8002/docs" 
	@echo "   - OCR Service:           http://localhost:8003/docs"
	@echo "   - Task Generator Service: http://localhost:8004/docs"
	@echo "   - RabbitMQ Management:   http://localhost:15672 (user/password)"
	@echo "   - Redis:                 localhost:6379"

down: ## Остановить все сервисы
	@echo "🛑 Остановка сервисов..."
	docker-compose down

logs: ## Показать логи всех сервисов
	docker-compose logs -f

test: ## Запустить end-to-end тест пайплайна
	@echo "🧪 Запуск тестирования пайплайна..."
	python test_pipeline.py

clean: ## Очистить Docker образы и volumes
	@echo "🧹 Очистка Docker..."
	docker-compose down -v
	docker system prune -f

status: ## Показать статус сервисов
	@echo "📊 Статус сервисов:"
	docker-compose ps

restart: ## Перезапустить все сервисы
	@echo "🔄 Перезапуск сервисов..."
	docker-compose restart

dev: ## Запуск в режиме разработки (с логами)
	@echo "💻 Запуск в режиме разработки..."
	docker-compose up
