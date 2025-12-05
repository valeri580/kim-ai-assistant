"""Тест подключений к OpenRouter и Telegram."""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from kim_core.config import load_config
from kim_core.llm import LLMRouter, OpenRouterClient
from kim_core.logging import init_logger, logger
from aiogram import Bot


async def test_openrouter():
    """Тест подключения к OpenRouter."""
    print("\n" + "=" * 50)
    print("Тест OpenRouter API")
    print("=" * 50)
    
    try:
        config = load_config()
        
        if not config.openrouter_api_key:
            print("✗ OPENROUTER_API_KEY не установлен")
            return False
        
        print(f"✓ API ключ найден: {config.openrouter_api_key[:20]}...")
        
        client = OpenRouterClient(config)
        router = LLMRouter(config, client)
        
        # Тестовый запрос
        print("Отправка тестового запроса...")
        messages = [
            {"role": "user", "content": "Привет! Ответь одним словом: работает?"}
        ]
        
        response = await router.run(messages, max_tokens=10)
        print(f"✓ OpenRouter работает!")
        print(f"  Ответ: {response}")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка OpenRouter: {e}")
        logger.exception("Детали ошибки:")
        return False


async def test_telegram():
    """Тест подключения к Telegram Bot API."""
    print("\n" + "=" * 50)
    print("Тест Telegram Bot API")
    print("=" * 50)
    
    try:
        config = load_config()
        
        if not config.telegram_bot_token:
            print("✗ BOT_TOKEN не установлен")
            return False
        
        print(f"✓ Токен бота найден: {config.telegram_bot_token[:10]}...")
        
        bot = Bot(token=config.telegram_bot_token)
        
        # Получаем информацию о боте
        print("Получение информации о боте...")
        me = await bot.get_me()
        
        print(f"✓ Telegram Bot API работает!")
        print(f"  Имя бота: {me.first_name}")
        print(f"  Username: @{me.username}")
        print(f"  ID: {me.id}")
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"✗ Ошибка Telegram: {e}")
        logger.exception("Детали ошибки:")
        return False


async def main():
    """Основная функция тестирования."""
    print("Проверка подключений...")
    
    # Инициализация логирования
    try:
        config = load_config()
        init_logger(config)
    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        return
    
    # Тесты
    telegram_ok = await test_telegram()
    openrouter_ok = await test_openrouter()
    
    # Итоги
    print("\n" + "=" * 50)
    print("Итоги проверки")
    print("=" * 50)
    print(f"Telegram: {'✓ Работает' if telegram_ok else '✗ Не работает'}")
    print(f"OpenRouter: {'✓ Работает' if openrouter_ok else '✗ Не работает'}")
    
    if telegram_ok and openrouter_ok:
        print("\n✓ Все подключения работают! Бот готов к запуску.")
        print("\nЗапустите бота командой:")
        print("  python -m src.kim_telegram.main")
    else:
        print("\n✗ Есть проблемы с подключениями. Проверьте конфигурацию.")


if __name__ == "__main__":
    asyncio.run(main())

