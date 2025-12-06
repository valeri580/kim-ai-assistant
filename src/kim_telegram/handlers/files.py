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
from kim_desktop.files.file_manager import (
    AliasNotFoundError,
    FileManagerError,
    PathTraversalError,
    find_latest_file,
    list_files,
    move_file,
    put_file,
    resolve_alias,
)
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


@router.message(Command("file_put"))
async def cmd_file_put(message: Message) -> None:
    """
    Обработчик команды /file_put.

    Формат: /file_put <local-path> <alias>
    Пример: /file_put C:\Users\User\Downloads\file.pdf documents
    """
    if _config is None:
        logger.error("Зависимости не инициализированы")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    command_text = message.text or ""
    parts = command_text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Используйте: `/file_put <путь_к_файлу> <alias>`\n\n"
            "Примеры:\n"
            "• `/file_put C:\\Users\\User\\Downloads\\file.pdf documents`\n"
            "• `/file_put D:\\Work\\report.docx desktop`\n\n"
            "Доступные alias: `downloads`, `desktop`, `documents`",
            parse_mode="Markdown",
        )
        return

    source_path_str = parts[1].strip()
    alias = parts[2].strip()

    if not source_path_str or not alias:
        await message.answer("❌ Путь к файлу и alias не могут быть пустыми.")
        return

    try:
        source_path = Path(source_path_str)
        result_path = put_file(source_path, alias)

        await message.answer(
            f"✅ Файл успешно скопирован в `{alias}`:\n"
            f"`{result_path}`",
            parse_mode="Markdown",
        )
        logger.info(f"Файл скопирован пользователем {message.from_user.id}: {source_path} -> {result_path}")

    except AliasNotFoundError as e:
        await message.answer(
            f"❌ Alias не найден: {alias}\n\n"
            f"Доступные alias: `downloads`, `desktop`, `documents`",
            parse_mode="Markdown",
        )
    except (FileManagerError, PathTraversalError) as e:
        await message.answer(f"❌ Ошибка при копировании файла: {str(e)}")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при обработке команды file_put: {e}")
        await message.answer("❌ Произошла неожиданная ошибка. Попробуйте позже.")


@router.message(Command("file_move"))
async def cmd_file_move(message: Message) -> None:
    """
    Обработчик команды /file_move.

    Формат: /file_move <src> <dest_alias>
    Пример: /file_move C:\Users\User\Downloads\file.pdf documents
    """
    if _config is None:
        logger.error("Зависимости не инициализированы")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    command_text = message.text or ""
    parts = command_text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Используйте: `/file_move <путь_к_файлу> <alias>`\n\n"
            "Примеры:\n"
            "• `/file_move C:\\Users\\User\\Downloads\\file.pdf documents`\n"
            "• `/file_move D:\\Work\\report.docx desktop`\n\n"
            "Доступные alias: `downloads`, `desktop`, `documents`",
            parse_mode="Markdown",
        )
        return

    source_path_str = parts[1].strip()
    alias = parts[2].strip()

    if not source_path_str or not alias:
        await message.answer("❌ Путь к файлу и alias не могут быть пустыми.")
        return

    try:
        source_path = Path(source_path_str)
        result_path = move_file(source_path, alias)

        await message.answer(
            f"✅ Файл успешно перемещён в `{alias}`:\n"
            f"`{result_path}`",
            parse_mode="Markdown",
        )
        logger.info(f"Файл перемещён пользователем {message.from_user.id}: {source_path} -> {result_path}")

    except AliasNotFoundError as e:
        await message.answer(
            f"❌ Alias не найден: {alias}\n\n"
            f"Доступные alias: `downloads`, `desktop`, `documents`",
            parse_mode="Markdown",
        )
    except (FileManagerError, PathTraversalError) as e:
        await message.answer(f"❌ Ошибка при перемещении файла: {str(e)}")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при обработке команды file_move: {e}")
        await message.answer("❌ Произошла неожиданная ошибка. Попробуйте позже.")


@router.message(Command("file_list"))
async def cmd_file_list(message: Message) -> None:
    """
    Обработчик команды /file_list.

    Формат: /file_list <alias> [pattern]
    Пример: /file_list documents
    Пример: /file_list downloads *.pdf
    """
    if _config is None:
        logger.error("Зависимости не инициализированы")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    command_text = message.text or ""
    parts = command_text.split(maxsplit=2)

    if len(parts) < 2:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Используйте: `/file_list <alias> [pattern]`\n\n"
            "Примеры:\n"
            "• `/file_list documents`\n"
            "• `/file_list downloads *.pdf`\n\n"
            "Доступные alias: `downloads`, `desktop`, `documents`",
            parse_mode="Markdown",
        )
        return

    alias = parts[1].strip()
    pattern = parts[2].strip() if len(parts) > 2 else None

    if not alias:
        await message.answer("❌ Alias не может быть пустым.")
        return

    try:
        files = list_files(alias, pattern)

        if not files:
            pattern_text = f" (шаблон: `{pattern}`)" if pattern else ""
            await message.answer(
                f"📁 В директории `{alias}` файлов не найдено{pattern_text}.",
                parse_mode="Markdown",
            )
            return

        # Формируем список файлов
        file_list = []
        for i, file_path in enumerate(files[:50], 1):  # Ограничиваем 50 файлами
            file_size = file_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            file_list.append(f"`{i}.` `{file_path.name}` ({size_mb:.2f} MB)")

        response = f"📁 Файлы в `{alias}`:\n\n" + "\n".join(file_list)

        if len(files) > 50:
            response += f"\n\n... и ещё {len(files) - 50} файлов"

        # Ограничиваем длину сообщения
        if len(response) > 4000:
            response = response[:3900] + "\n\n... (список обрезан)"

        await message.answer(response, parse_mode="Markdown")
        logger.info(f"Список файлов отправлен пользователю {message.from_user.id} для alias: {alias}")

    except AliasNotFoundError as e:
        await message.answer(
            f"❌ Alias не найден: {alias}\n\n"
            f"Доступные alias: `downloads`, `desktop`, `documents`",
            parse_mode="Markdown",
        )
    except FileManagerError as e:
        await message.answer(f"❌ Ошибка при получении списка файлов: {str(e)}")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при обработке команды file_list: {e}")
        await message.answer("❌ Произошла неожиданная ошибка. Попробуйте позже.")

