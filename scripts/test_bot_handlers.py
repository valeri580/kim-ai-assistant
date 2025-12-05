"""Тест обработчиков бота."""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from kim_core.config import load_config
from kim_core.logging import init_logger, logger
from aiogram import Bot
from aiogram.types import Message, User, Chat
from unittest.mock import AsyncMock, MagicMock

# Импортируем обработчики
from kim_telegram.handlers.common import router, init_dependencies
from kim_telegram.storage.memory import InMemoryDialogStore
from kim_core.llm import LLMRouter, OpenRouterClient


async def test_start_command():
    """Тест команды /start."""
    print("\n" + "=" * 50)
    print("Тест команды /start")
    print("=" * 50)
    
    try:
        config = load_config()
        init_logger(config)
        
        # Создаём моки
        mock_message = AsyncMock(spec=Message)
        mock_message.from_user = MagicMock(spec=User)
        mock_message.from_user.id = 12345
        mock_message.answer = AsyncMock()
        
        # Инициализируем зависимости
        try:
            client = OpenRouterClient(config)
            llm_router = LLMRouter(config, client)
        except Exception as e:
            print(f"⚠ Не удалось создать LLM клиент (это нормально для теста): {e}")
            llm_router = None
        
        dialog_store = InMemoryDialogStore()
        init_dependencies(dialog_store, llm_router)
        
        # Находим обработчик команды /start
        from aiogram.filters import Command
        
        # Проверяем, что обработчик зарегистрирован
        print(f"Количество обработчиков в роутере: {len(router.sub_routers)}")
        
        # Пробуем вызвать обработчик напрямую
        from kim_telegram.handlers.common import cmd_start
        
        await cmd_start(mock_message)
        
        # Проверяем, что answer был вызван
        if mock_message.answer.called:
            print("✓ Команда /start обработана!")
            print(f"  Ответ: {mock_message.answer.call_args}")
            return True
        else:
            print("✗ Команда /start не вызвала answer()")
            return False
            
    except Exception as e:
        print(f"✗ Ошибка при тесте: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_bot_connection():
    """Тест подключения к боту."""
    print("\n" + "=" * 50)
    print("Тест подключения к Telegram Bot API")
    print("=" * 50)
    
    try:
        config = load_config()
        
        if not config.telegram_bot_token:
            print("✗ BOT_TOKEN не установлен")
            return False
        
        bot = Bot(token=config.telegram_bot_token)
        me = await bot.get_me()
        
        print(f"✓ Бот подключён: @{me.username} ({me.first_name})")
        print(f"  ID: {me.id}")
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"✗ Ошибка подключения: {e}")
        return False


async def main():
    """Основная функция."""
    print("Проверка обработчиков бота...")
    
    # Тест подключения
    connection_ok = await test_bot_connection()
    
    # Тест обработчика
    handler_ok = await test_start_command()
    
    print("\n" + "=" * 50)
    print("Итоги")
    print("=" * 50)
    print(f"Подключение к Telegram: {'✓ OK' if connection_ok else '✗ Ошибка'}")
    print(f"Обработчик /start: {'✓ OK' if handler_ok else '✗ Ошибка'}")
    
    if connection_ok and handler_ok:
        print("\n✓ Всё работает! Проблема может быть в запуске бота.")
        print("  Убедитесь, что бот запущен: python -m src.kim_telegram.main")
    else:
        print("\n✗ Есть проблемы, которые нужно исправить.")


if __name__ == "__main__":
    asyncio.run(main())

