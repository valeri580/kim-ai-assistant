.PHONY: install bot voice diag test help

# Установка зависимостей
install:
	pip install -r requirements.txt

# Запуск Telegram-бота
bot:
	python -m scripts.run_telegram_bot

# Запуск голосового ассистента
voice:
	python -m scripts.run_voice_assistant

# Запуск сервиса диагностики
diag:
	python -m scripts.run_diagnostics_service

# Запуск тестов
test:
	pytest tests/ -v

# Справка
help:
	@echo "Доступные команды:"
	@echo "  make install  - Установить зависимости"
	@echo "  make bot      - Запустить Telegram-бота"
	@echo "  make voice    - Запустить голосового ассистента"
	@echo "  make diag     - Запустить сервис диагностики"
	@echo "  make test     - Запустить тесты"
	@echo "  make help     - Показать эту справку"

