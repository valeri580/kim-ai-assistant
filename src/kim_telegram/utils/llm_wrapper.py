"""Утилиты для обёртки LLM-вызовов с таймаутом и обработкой ошибок."""

import asyncio
from typing import TypeVar, Awaitable

from aiogram.types import Message

from kim_core.llm import BudgetExceededError, LLMError
from kim_core.logging import logger

# Пробуем импортировать httpx.ReadTimeout (может быть не установлен)
try:
    from httpx import ReadTimeout
except ImportError:
    ReadTimeout = type("ReadTimeout", (TimeoutError,), {})

T = TypeVar("T")


async def wrap_llm_call(
    message: Message,
    coro: Awaitable[T],
    timeout_seconds: float = 15.0,
    timeout_message: str = "Превышено время ожидания ответа от модели. Попробуйте ещё раз.",
) -> T:
    """
    Обёртка для LLM-вызовов с таймаутом и обработкой ошибок.

    Перед вызовом отправляет typing... в чат.
    Оборачивает вызов в таймаут и обрабатывает все исключения.

    Args:
        message: Сообщение Telegram для отправки typing... и ответа
        coro: Асинхронная корутина для выполнения
        timeout_seconds: Таймаут в секундах (по умолчанию 15)
        timeout_message: Сообщение при таймауте

    Returns:
        Результат выполнения корутины

    Raises:
        BudgetExceededError: При превышении лимита токенов (пробрасывается дальше)
        LLMError: При ошибках LLM (пробрасывается дальше)
        TimeoutError: При таймауте (обрабатывается внутри, отправляет сообщение пользователю)
    """
    user_id = message.from_user.id if message.from_user else None

    # Отправляем typing...
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
    except Exception as e:
        logger.warning(f"Не удалось отправить typing... для пользователя {user_id}: {e}")

    try:
        # Выполняем корутину с таймаутом
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        return result

    except asyncio.TimeoutError:
        logger.warning(
            f"Таймаут LLM-вызова для пользователя {user_id} "
            f"(превышено {timeout_seconds} секунд)"
        )
        try:
            await message.answer(timeout_message)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о таймауте пользователю {user_id}: {e}")
        raise

    except TimeoutError:
        # Обрабатываем TimeoutError (может быть от httpx или других библиотек)
        logger.warning(
            f"Таймаут LLM-вызова для пользователя {user_id} "
            f"(превышено {timeout_seconds} секунд)"
        )
        try:
            await message.answer(timeout_message)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о таймауте пользователю {user_id}: {e}")
        raise

    except ReadTimeout:
        # Обрабатываем httpx.ReadTimeout
        logger.warning(
            f"Таймаут чтения HTTP для пользователя {user_id} "
            f"(превышено {timeout_seconds} секунд)"
        )
        try:
            await message.answer(timeout_message)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о таймауте пользователю {user_id}: {e}")
        raise

    except BudgetExceededError:
        # Пробрасываем BudgetExceededError дальше для обработки в обработчике
        raise

    except LLMError:
        # Пробрасываем LLMError дальше для обработки в обработчике
        raise

    except Exception as e:
        # Логируем все остальные исключения, но не ломаем цикл бота
        logger.exception(
            f"Неожиданная ошибка при LLM-вызове для пользователя {user_id}: {e}"
        )
        try:
            await message.answer(
                "Ким сейчас не может ответить из-за ошибки, попробуйте позже."
            )
        except Exception as send_error:
            logger.error(
                f"Не удалось отправить сообщение об ошибке пользователю {user_id}: {send_error}"
            )
        raise

