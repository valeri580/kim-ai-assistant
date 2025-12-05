"""Проверка конфигурации перед запуском."""

from kim_core.config import load_config

try:
    config = load_config()
    print("✓ Конфигурация загружена успешно")
    print(f"  MODE: {config.mode}")
    print(f"  LOG_LEVEL: {config.log_level}")
    print(f"  BOT_TOKEN: {'✓ установлен' if config.telegram_bot_token else '✗ не установлен'}")
    print(f"  OPENROUTER_API_KEY: {'✓ установлен' if config.openrouter_api_key else '✗ не установлен'}")
    print(f"  MODEL_FAST: {config.model_fast}")
    print(f"  MODEL_SMART: {config.model_smart}")
    print(f"  TOKEN_BUDGET_DAILY: {config.token_budget_daily}")
except Exception as e:
    print(f"✗ Ошибка загрузки конфигурации: {e}")
    exit(1)

