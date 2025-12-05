"""Проверка статуса бота."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from kim_core.config import load_config
from aiogram import Bot


async def check_bot():
    """Проверка работы бота."""
    try:
        config = load_config()
        bot = Bot(token=config.telegram_bot_token)
        me = await bot.get_me()
        print(f"✓ Бот работает: @{me.username} ({me.first_name})")
        print(f"  ID: {me.id}")
        await bot.session.close()
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(check_bot())

