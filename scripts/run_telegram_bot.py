"""Скрипт запуска Telegram-бота."""

import sys
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger, logger
from kim_telegram.main import main as telegram_main
import asyncio


def main() -> None:
    """Запуск Telegram-бота."""
    # Загрузка конфигурации и инициализация логирования
    config = load_config()
    init_logger(config)
    
    logger.info("=" * 60)
    logger.info("Starting Telegram bot...")
    logger.info("=" * 60)
    
    try:
        asyncio.run(telegram_main())
    except KeyboardInterrupt:
        logger.info("Остановка Telegram-бота по запросу пользователя")
    except Exception as e:
        logger.exception(f"Telegram bot crashed: {e}")
        print(f"\n❌ Telegram-бот не смог запуститься. Проверьте BOT_TOKEN и настройки.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

