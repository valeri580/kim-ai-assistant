"""Тест подключения к OpenRouter API."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from kim_core.config import load_config
from kim_core.llm import LLMRouter, OpenRouterClient
from kim_core.logging import init_logger, logger


async def test_openrouter():
    """Тест подключения к OpenRouter API."""
    print("\n" + "=" * 60)
    print("Тест подключения к OpenRouter API")
    print("=" * 60)
    
    try:
        config = load_config()
        init_logger(config)
        
        if not config.openrouter_api_key:
            print("✗ OPENROUTER_API_KEY не установлен в .env")
            return False
        
        print(f"✓ API ключ найден: {config.openrouter_api_key[:20]}...")
        print(f"  Быстрая модель: {config.model_fast}")
        print(f"  Умная модель: {config.model_smart}")
        print(f"  Дневной лимит токенов: {config.token_budget_daily}")
        
        print("\nИнициализация клиента OpenRouter...")
        client = OpenRouterClient(config)
        
        print("Создание маршрутизатора...")
        router = LLMRouter(config, client)
        
        # Тестовый запрос
        print("\nОтправка тестового запроса...")
        messages = [
            {"role": "user", "content": "Привет! Ответь одним коротким словом: работает?"}
        ]
        
        print("Ожидание ответа от OpenRouter...")
        response = await router.run(messages, max_tokens=20)
        
        print("\n" + "=" * 60)
        print("✓ OpenRouter API работает!")
        print("=" * 60)
        print(f"Ответ от LLM: {response}")
        print(f"\nМодель, использованная для запроса: {config.model_fast}")
        
        # Проверка баланса через информацию об использовании
        print("\n" + "-" * 60)
        print("Информация о подключении:")
        print("-" * 60)
        print("✓ API ключ валиден")
        print("✓ Запрос успешно выполнен")
        print("✓ Получен ответ от модели")
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ Ошибка подключения к OpenRouter")
        print("=" * 60)
        print(f"Тип ошибки: {type(e).__name__}")
        print(f"Сообщение: {e}")
        
        logger.exception("Детали ошибки:")
        
        # Дополнительные советы
        print("\n" + "-" * 60)
        print("Возможные причины:")
        print("-" * 60)
        print("1. Неправильный API ключ — проверьте OPENROUTER_API_KEY в .env")
        print("2. Нет средств на балансе — проверьте баланс на https://openrouter.ai/credits")
        print("3. Неправильное имя модели — проверьте MODEL_FAST и MODEL_SMART в .env")
        print("4. Проблемы с сетью — проверьте интернет-соединение")
        
        return False


async def main():
    """Основная функция."""
    print("Проверка подключения к OpenRouter...")
    
    try:
        config = load_config()
        init_logger(config)
    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        return
    
    success = await test_openrouter()
    
    print("\n" + "=" * 60)
    print("Итоги проверки")
    print("=" * 60)
    if success:
        print("✓ Подключение к OpenRouter работает корректно!")
        print("\nВы можете использовать бота и голосовой ассистент.")
    else:
        print("✗ Есть проблемы с подключением к OpenRouter.")
        print("  Проверьте конфигурацию и баланс на https://openrouter.ai/credits")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

