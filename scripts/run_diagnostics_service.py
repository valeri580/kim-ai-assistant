"""Скрипт запуска сервиса диагностики системы."""

import sys
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger, logger
from kim_scheduler.diagnostics_watcher import main as diagnostics_main
import asyncio


def main() -> None:
    """Запуск сервиса диагностики."""
    # Загрузка конфигурации и инициализация логирования
    config = load_config()
    init_logger(config)
    
    logger.info("=" * 60)
    logger.info("Starting diagnostics watcher...")
    logger.info("=" * 60)
    
    try:
        asyncio.run(diagnostics_main())
    except KeyboardInterrupt:
        logger.info("Остановка сервиса диагностики по запросу пользователя")
        print("\nОстановка сервиса диагностики...")
    except Exception as e:
        logger.exception(f"Diagnostics service crashed: {e}")
        print(f"\n❌ Сервис диагностики не смог запуститься: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

