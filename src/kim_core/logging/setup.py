"""Настройка логирования."""

import sys
import os

from loguru import logger

from kim_core.config.settings import AppConfig


def _setup_console_encoding() -> None:
    """
    Настраивает кодировку консоли для корректного отображения UTF-8.
    
    В Windows консоль по умолчанию может использовать не UTF-8,
    что приводит к некорректному отображению русских символов.
    """
    if sys.platform == "win32":
        try:
            # Устанавливаем переменную окружения для UTF-8
            os.environ["PYTHONIOENCODING"] = "utf-8"
            
            # Устанавливаем кодировку консоли через системный вызов chcp 65001
            # Это устанавливает UTF-8 в Windows консоли
            try:
                import subprocess
                # Используем os.system для более надёжного вызова
                os.system("chcp 65001 >nul 2>&1")
            except Exception:
                pass
            
            # Пытаемся установить кодировку через reconfigure
            # Это работает в Python 3.7+
            try:
                if hasattr(sys.stdout, 'reconfigure'):
                    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                if hasattr(sys.stderr, 'reconfigure'):
                    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, ValueError):
                pass
        except Exception:
            # Если что-то пошло не так, продолжаем без изменений
            pass


def init_logger(config: AppConfig) -> None:
    """
    Инициализирует логгер на основе конфигурации.

    Args:
        config: Конфигурация приложения
    """
    # Настраиваем кодировку консоли для Windows
    _setup_console_encoding()
    
    # Удаляем стандартный обработчик loguru
    logger.remove()

    # Добавляем обработчик с настраиваемым уровнем
    # Используем стандартный stderr - loguru правильно обработает UTF-8
    # после настройки кодировки консоли
    logger.add(
        sys.stderr,
        level=config.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        colorize=True,
    )

    # Логируем информацию о запуске
    logger.info(f"Режим работы: {config.mode}")
    logger.info(f"Уровень логирования: {config.log_level}")
    logger.info(f"Быстрая модель: {config.model_fast}")
    logger.info(f"Умная модель: {config.model_smart}")
    logger.info(f"Дневной лимит токенов: {config.token_budget_daily}")

