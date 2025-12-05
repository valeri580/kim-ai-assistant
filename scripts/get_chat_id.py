"""Утилита для получения Telegram Chat ID.

Этот скрипт поможет вам определить ваш Chat ID для настройки ALERTS_CHAT_ID в .env.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from aiogram import Bot
from aiogram.types import Update


async def get_chat_id_from_message(bot: Bot) -> None:
    """
    Получает Chat ID из первого полученного сообщения.
    
    Инструкция:
    1. Запустите этот скрипт
    2. Отправьте любое сообщение вашему боту в Telegram
    3. Скрипт покажет ваш Chat ID
    """
    print("\n" + "=" * 60)
    print("Получение Chat ID из сообщения")
    print("=" * 60)
    print("\n1. Убедитесь, что ваш бот запущен (python run_bot.py)")
    print("2. Отправьте любое сообщение вашему боту в Telegram")
    print("3. Этот скрипт покажет ваш Chat ID")
    print("\nОжидание сообщения... (нажмите Ctrl+C для отмены)\n")

    chat_id_received = False

    async def message_handler(update: Update) -> None:
        nonlocal chat_id_received
        
        if update.message:
            chat_id = update.message.chat.id
            user_id = update.message.from_user.id if update.message.from_user else None
            
            print("\n" + "=" * 60)
            print("✓ Chat ID найден!")
            print("=" * 60)
            print(f"\nВаш Chat ID: {chat_id}")
            if user_id:
                print(f"Ваш User ID: {user_id}")
            print(f"\nДобавьте в файл .env:")
            print(f"ALERTS_CHAT_ID={chat_id}")
            print("\n" + "=" * 60)
            chat_id_received = True

    # Для этого метода нужен активный бот, поэтому показываем альтернативные способы
    print("\n⚠️  Этот метод требует запущенного бота.")
    print("Используйте альтернативные способы ниже.\n")


async def show_alternative_methods() -> None:
    """Показывает альтернативные способы получения Chat ID."""
    print("\n" + "=" * 60)
    print("Способы получения Telegram Chat ID")
    print("=" * 60)
    
    print("\n📱 СПОСОБ 1: Через бота @userinfobot (Самый простой)")
    print("-" * 60)
    print("1. Откройте Telegram")
    print("2. Найдите бота: @userinfobot")
    print("3. Нажмите 'Start' или отправьте команду /start")
    print("4. Бот вернёт ваш ID, например: 123456789")
    print("5. Добавьте в .env: ALERTS_CHAT_ID=123456789")
    
    print("\n📱 СПОСОБ 2: Через бота @RawDataBot")
    print("-" * 60)
    print("1. Откройте Telegram")
    print("2. Найдите бота: @RawDataBot")
    print("3. Нажмите 'Start'")
    print("4. Отправьте любое сообщение")
    print("5. Бот вернёт JSON с вашим ID в поле 'id'")
    
    print("\n🤖 СПОСОБ 3: Через вашего бота (если он запущен)")
    print("-" * 60)
    print("1. Убедитесь, что ваш бот запущен: python run_bot.py")
    print("2. Отправьте любое сообщение вашему боту")
    print("3. В логах бота будет виден ваш Chat ID")
    print("   Ищите строку вида: 'user_id=123456789' или 'chat_id=123456789'")
    
    print("\n💻 СПОСОБ 4: Программно (если у вас есть доступ к API)")
    print("-" * 60)
    print("1. Отправьте сообщение вашему боту")
    print("2. Используйте скрипт ниже для получения ID из логов")
    
    print("\n" + "=" * 60)
    print("После получения ID добавьте в .env файл:")
    print("=" * 60)
    print("ALERTS_CHAT_ID=ваш_номер_id")
    print("\n")


async def check_existing_chat_id() -> None:
    """Проверяет, задан ли уже Chat ID в конфигурации."""
    try:
        config = load_config()
        if config.alerts_chat_id:
            print(f"\n✓ Chat ID уже задан в конфигурации: {config.alerts_chat_id}")
        else:
            print("\n⚠️  Chat ID не задан в конфигурации")
    except Exception as e:
        print(f"\n⚠️  Ошибка загрузки конфигурации: {e}")


async def main() -> None:
    """Главная функция."""
    print("\n🔍 Утилита получения Telegram Chat ID")
    
    # Проверяем существующий Chat ID
    await check_existing_chat_id()
    
    # Показываем способы получения
    await show_alternative_methods()
    
    # Пытаемся проверить бота
    try:
        config = load_config()
        if config.telegram_bot_token:
            print("\n✓ Токен бота найден в конфигурации")
            print("\n💡 Совет: Отправьте сообщение вашему боту и проверьте логи бота.")
            print("   В логах будет виден ваш Chat ID при получении сообщения.")
        else:
            print("\n⚠️  Токен бота не найден в конфигурации")
            print("   Убедитесь, что BOT_TOKEN указан в файле .env")
    except Exception as e:
        print(f"\n⚠️  Ошибка: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nОтмена...")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)

