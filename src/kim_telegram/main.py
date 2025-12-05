"""Точка входа Telegram-бота."""

import asyncio

from aiogram import Bot, Dispatcher

from kim_core.config import AppConfig, load_config
from kim_core.llm import LLMRouter, OpenRouterClient
from kim_core.logging import init_logger, logger
from kim_telegram.handlers.common import init_dependencies, router
from kim_telegram.storage.memory import InMemoryDialogStore


async def main() -> None:
    """Основная функция запуска бота."""
    # Загрузка конфигурации
    config = load_config()

    # Инициализация логирования
    init_logger(config)

    # Проверка наличия токена бота
    if not config.telegram_bot_token:
        error_msg = "BOT_TOKEN не установлен в конфигурации"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Инициализация Telegram-бота...")

    # Создание клиента OpenRouter и маршрутизатора
    try:
        client = OpenRouterClient(config)
        llm_router = LLMRouter(config, client)
        logger.info("LLM-клиент инициализирован")
    except Exception as e:
        logger.error(f"Ошибка инициализации LLM: {e}")
        raise

    # Создание хранилища диалогов
    dialog_store = InMemoryDialogStore()

    # Инициализация зависимостей для обработчиков
    init_dependencies(dialog_store, llm_router)

    # Создание бота и диспетчера
    bot = Bot(token=config.telegram_bot_token)
    dp = Dispatcher()

    # Регистрация роутера
    dp.include_router(router)
    
    logger.info("Роутер зарегистрирован в диспетчере")

    # Получаем информацию о боте для подтверждения
    bot_info = await bot.get_me()
    logger.info(
        f"Telegram-бот запущен и готов к работе: @{bot_info.username} "
        f"({bot_info.first_name})"
    )
    logger.info("Ожидание сообщений...")

    try:
        # Запуск long polling
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        await bot.session.close()
        logger.info("Сессия бота закрыта")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота по запросу пользователя")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        raise

