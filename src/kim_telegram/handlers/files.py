"""Обработчики команд для работы с файлами."""

import asyncio
from pathlib import Path
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from kim_core.config.settings import AppConfig
from kim_core.llm import LLMRouter
from kim_core.logging import logger
from kim_desktop.files.reader import (
    FileAccessError,
    FileTypeNotSupportedError,
    read_file_text,
)
from kim_desktop.files.summarizer import summarize_text_with_llm
from kim_telegram.utils.llm_wrapper import wrap_llm_call

router = Router()

# Глобальные зависимости (устанавливаются при инициализации бота)
_config: Optional[AppConfig] = None
_llm_router: Optional[LLMRouter] = None


def init_file_dependencies(config: AppConfig, llm_router: LLMRouter) -> None:
    """
    Инициализирует зависимости для обработчиков файлов.

    Args:
        config: Конфигурация приложения
        llm_router: Маршрутизатор LLM
    """
    global _config, _llm_router
    _config = config
    _llm_router = llm_router
    logger.info("Зависимости для обработчиков файлов инициализированы")


@router.message(Command("file_summary"))
async def cmd_file_summary(message: Message) -> None:
    """
    Обработчик команды /file_summary.

    Формат: /file_summary <путь_к_файлу>
    Пример: /file_summary C:\Users\User\Documents\report.pdf
    """
    if _config is None or _llm_router is None:
        logger.error("Зависимости не инициализированы")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    # Извлекаем путь к файлу из команды
    command_text = message.text or ""
    parts = command_text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Используйте: `/file_summary <путь_к_файлу>`\n\n"
            "Примеры:\n"
            "• `/file_summary C:\\Users\\User\\Documents\\report.pdf`\n"
            "• `/file_summary D:\\Work\\docs\\notes.txt`\n\n"
            "⚠️ Файл должен находиться в одной из разрешённых директорий, "
            "указанных в FILE_WHITELIST_DIRS.",
            parse_mode="Markdown",
        )
        return

    file_path_str = parts[1].strip()

    if not file_path_str:
        await message.answer("❌ Путь к файлу не может быть пустым.")
        return

    try:
        # Преобразуем строку в Path
        file_path = Path(file_path_str)
        
        logger.info(
            f"Запрос на резюме файла от пользователя {message.from_user.id}: {file_path}"
        )

        # Читаем файл
        try:
            file_text = read_file_text(file_path, _config)
            logger.info(f"Файл успешно прочитан: {file_path}, размер текста: {len(file_text)} символов")
        except FileTypeNotSupportedError as e:
            logger.warning(f"Неподдерживаемый тип файла: {file_path}")
            await message.answer(
                f"❌ Этот тип файла пока не поддерживается.\n\n"
                f"Поддерживаются: `.txt`, `.md`, `.pdf`, `.docx`.\n\n"
                f"Детали: {str(e)}"
            )
            return
        except FileAccessError as e:
            logger.warning(f"Ошибка доступа к файлу: {file_path}, ошибка: {e}")
            await message.answer(
                "❌ Не могу прочитать этот файл.\n\n"
                "Убедитесь, что:\n"
                "• Файл существует\n"
                "• Файл находится в одной из разрешённых директорий (FILE_WHITELIST_DIRS)\n"
                "• Размер файла не превышает ограничение (FILE_MAX_SIZE_MB)\n\n"
                f"Детали: {str(e)}"
            )
            return

        # Генерируем резюме через LLM с таймаутом через обёртку
        try:
            summary = await wrap_llm_call(
                message,
                summarize_text_with_llm(file_text, _llm_router, _config),
                timeout_seconds=_config.llm_timeout_seconds,
                timeout_message="Превышено время ожидания генерации резюме. Попробуйте ещё раз.",
            )
            logger.info(f"Резюме успешно сгенерировано для файла: {file_path}")
        except (TimeoutError, asyncio.TimeoutError):
            # Таймаут уже обработан в wrap_llm_call
            return
        except Exception as e:
            logger.exception(f"Ошибка при генерации резюме: {e}")
            # Ошибка уже обработана в wrap_llm_call
            return

        # Отправляем результат пользователю
        file_name = file_path.name
        response = f"📄 Резюме файла `{file_name}`:\n\n{summary}"

        # Ограничиваем длину сообщения (Telegram лимит ~4096 символов)
        if len(response) > 4000:
            response = response[:3900] + "\n\n... (сообщение обрезано)"

        await message.answer(response, parse_mode="Markdown")
        logger.info(f"Резюме отправлено пользователю {message.from_user.id}")

    except Exception as e:
        # Все остальные исключения уже обработаны в wrap_llm_call или выше
        logger.exception(f"Неожиданная ошибка при обработке команды file_summary: {e}")

