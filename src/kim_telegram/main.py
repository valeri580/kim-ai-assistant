"""Точка входа Telegram-бота."""

import asyncio

from aiogram import Bot, Dispatcher

from kim_core.config import AppConfig, load_config
from kim_core.llm import LLMRouter, OpenRouterClient
from kim_core.logging import init_logger, logger
from kim_scheduler.calendar.service import CalendarService
from kim_scheduler.calendar.storage import CalendarStorage
from kim_telegram.handlers.common import init_dependencies, router
from kim_telegram.handlers.files import init_file_dependencies, router as files_router
from kim_telegram.handlers.reminders import init_calendar_service, router as reminders_router
from kim_telegram.handlers.web_search import init_web_search_client, router as web_search_router
from kim_telegram.storage.memory import InMemoryDialogStore
from kim_tools.web_search.client import WebSearchClient
from kim_tools.web_search.tools import WebSearchTool


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

    # Создание клиента веб-поиска
    web_search_client = WebSearchClient(
        api_key=config.serpapi_key,
        timeout=10,
    )
    init_web_search_client(web_search_client, config)
    logger.info("WebSearchClient инициализирован")

    # Создание клиента OpenRouter и маршрутизатора
    try:
        client = OpenRouterClient(config)
        llm_router = LLMRouter(config, client)
        
        # Регистрируем инструмент веб-поиска в LLMRouter
        web_search_tool = WebSearchTool(web_search_client)
        llm_router.register_tool(web_search_tool)
        logger.info("Инструмент web_search зарегистрирован в LLMRouter")
        
        logger.info("LLM-клиент инициализирован")
    except Exception as e:
        logger.error(f"Ошибка инициализации LLM: {e}")
        raise

    # Создание хранилища диалогов
    dialog_store = InMemoryDialogStore()

    # Инициализация зависимостей для обработчиков
    init_dependencies(dialog_store, llm_router, config)
    
    # Инициализация зависимостей для обработчиков файлов
    init_file_dependencies(config, llm_router)
    logger.info("Обработчики файлов инициализированы")

    # Создание хранилища и сервиса календаря
    calendar_storage = CalendarStorage(config.reminders_db_path)
    calendar_service = CalendarService(calendar_storage)
    init_calendar_service(calendar_service)
    logger.info("Сервис календаря инициализирован")

    # Создание бота и диспетчера
    bot = Bot(token=config.telegram_bot_token)
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(router)
    dp.include_router(reminders_router)
    dp.include_router(web_search_router)
    dp.include_router(files_router)
    
    logger.info("Роутеры зарегистрированы в диспетчере")

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

