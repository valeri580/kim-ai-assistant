"""Обработчики команд для веб-поиска."""

import asyncio
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

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
        
        # Нормализуем результаты
        normalized = normalize_results(results, limit=5)
        
        if not normalized:
            await message.answer(
                f"🔍 По запросу «{query}» ничего не найдено.\n\n"
                "Попробуйте изменить формулировку запроса."
            )
            return
        
        # Форматируем ответ: title + url для каждого результата
        response_parts = [f"🔍 Найдено {len(normalized)} результатов по запросу «{query}»:\n"]
        
        for i, result in enumerate(normalized, 1):
            title = result.get("title", "Без заголовка")
            url = result.get("url", "") or result.get("link", "")
            source_name = result.get("source_name", "")
            
            # Формат: 1) <title>\n   <url>
            response_parts.append(f"\n{i}) *{title}*")
            if url:
                response_parts.append(f"   `{url}`")
            if source_name:
                response_parts.append(f"   _{source_name}_")
        
        response = "\n".join(response_parts)
        
        # Ограничиваем длину сообщения (Telegram имеет лимит ~4096 символов)
        if len(response) > 4000:
            response = response[:3900] + "\n\n... (сообщение обрезано)"
        
        # Создаём кнопки для результатов
        keyboard_buttons = []
        
        # Добавляем кнопку "Открыть в браузере" для первого результата
        if normalized and (normalized[0].get("url") or normalized[0].get("link")):
            first_url = normalized[0].get("url") or normalized[0].get("link")
            keyboard_buttons.append([InlineKeyboardButton(
                text="🌐 Открыть в браузере",
                url=first_url
            )])
        
        # Добавляем кнопки для остальных результатов (максимум 3 дополнительных)
        for result in normalized[1:4]:  # Пропускаем первый, берём до 3 дополнительных
            url = result.get("url", "") or result.get("link", "")
            if url:
                title = result.get("title", "Открыть")
                # Сокращаем длину заголовка для кнопки
                if len(title) > 40:
                    title = title[:37] + "..."
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"🔗 {title}",
                    url=url
                )])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
        
        await message.answer(
            response,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        logger.info(f"Веб-поиск выполнен: найдено {len(normalized)} результатов")

    except (TimeoutError, asyncio.TimeoutError):
        # Таймаут уже обработан в wrap_llm_call, сообщение пользователю отправлено
        pass

    except Exception:
        # Все остальные исключения уже обработаны в wrap_llm_call
        # Сообщение пользователю уже отправлено, просто логируем для отладки
        pass

