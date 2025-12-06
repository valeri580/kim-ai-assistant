"""Обработчики команд для веб-поиска."""

import asyncio
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from kim_core.config.settings import AppConfig
from kim_core.logging import logger
from kim_telegram.utils.llm_wrapper import wrap_llm_call
from kim_tools.web_search.client import WebSearchClient
from kim_tools.web_search.parser import normalize_results, summarize_results

router = Router()

# Глобальные зависимости (устанавливаются при инициализации бота)
_web_search_client: Optional[WebSearchClient] = None
_config: Optional[AppConfig] = None


def init_web_search_client(client: WebSearchClient, config: AppConfig) -> None:
    """
    Инициализирует клиент веб-поиска для обработчиков.

    Args:
        client: Клиент веб-поиска
        config: Конфигурация приложения
    """
    global _web_search_client, _config
    _web_search_client = client
    _config = config
    logger.info("WebSearchClient инициализирован для обработчиков")


@router.message(Command("web"))
async def cmd_web(message: Message) -> None:
    """
    Обработчик команды /web.

    Формат: /web <запрос>
    Пример: /web погода в Москве
    """
    if _web_search_client is None:
        logger.error("WebSearchClient не инициализирован")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    # Извлекаем текст запроса (после /web)
    command_text = message.text or ""
    parts = command_text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Используйте: `/web <запрос>`\n\n"
            "Примеры:\n"
            "• `/web погода в Москве`\n"
            "• `/web последние новости про искусственный интеллект`",
            parse_mode="Markdown",
        )
        return

    query = parts[1].strip()

    if not query:
        await message.answer("❌ Запрос не может быть пустым.")
        return

    if _config is None:
        logger.error("Конфигурация не инициализирована")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    try:
        logger.info(f"Выполнение веб-поиска: query='{query}'")
        
        # Выполняем поиск с таймаутом через обёртку
        results = await wrap_llm_call(
            message,
            _web_search_client.search(query, num_results=5),
            timeout_seconds=_config.llm_timeout_seconds,
            timeout_message="Превышено время ожидания ответа от поиска. Попробуйте ещё раз.",
        )
        
        if not results:
            await message.answer(
                f"🔍 По запросу «{query}» ничего не найдено.\n\n"
                "Попробуйте изменить формулировку запроса."
            )
            return

        # Нормализуем результаты
        normalized = normalize_results(results, limit=5)
        
        # Создаём краткое описание
        summary = summarize_results(normalized)
        
        # Форматируем ответ
        response = f"🔍 Вот что удалось найти по запросу «{query}»:\n\n{summary}"
        
        # Ограничиваем длину сообщения (Telegram имеет лимит ~4096 символов)
        if len(response) > 4000:
            response = response[:3900] + "\n\n... (сообщение обрезано)"
        
        await message.answer(response)
        logger.info(f"Веб-поиск выполнен: найдено {len(normalized)} результатов")

    except (TimeoutError, asyncio.TimeoutError):
        # Таймаут уже обработан в wrap_llm_call, сообщение пользователю отправлено
        pass

    except Exception:
        # Все остальные исключения уже обработаны в wrap_llm_call
        # Сообщение пользователю уже отправлено, просто логируем для отладки
        pass

