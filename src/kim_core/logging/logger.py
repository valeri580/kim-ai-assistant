"""Настройка логирования."""

from loguru import logger

from kim_core.config.settings import AppConfig


def init_logger(config: AppConfig) -> None:
    """
    Инициализирует логгер на основе конфигурации.

    Args:
        config: Конфигурация приложения
    """
    # Удаляем стандартный обработчик loguru
    logger.remove()

    # Добавляем обработчик с настраиваемым уровнем
    logger.add(
        lambda msg: print(msg, end=""),
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

