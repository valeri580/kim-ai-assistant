"""Обработчики команд и сообщений Telegram-бота."""

from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from kim_core.llm import BudgetExceededError, LLMError, LLMRouter
from kim_core.logging import logger
from kim_core.prompts import get_system_prompt
from kim_telegram.storage.memory import InMemoryDialogStore

router = Router()

# Глобальные зависимости (устанавливаются при инициализации бота)
_dialog_store: Optional[InMemoryDialogStore] = None
_llm_router: Optional[LLMRouter] = None


def init_dependencies(
    dialog_store: InMemoryDialogStore, llm_router: LLMRouter
) -> None:
    """
    Инициализирует зависимости для обработчиков.

    Args:
        dialog_store: Хранилище контекста диалогов
        llm_router: Маршрутизатор LLM
    """
    global _dialog_store, _llm_router
    _dialog_store = dialog_store
    _llm_router = llm_router
    logger.info("Зависимости для обработчиков инициализированы")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start."""
    logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
    await message.answer(
        "Привет! Я Ким, твой персональный ассистент. "
        "Можешь задавать мне вопросы, и я постараюсь помочь.\n\n"
        "Используй /help, чтобы увидеть все доступные команды."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help — показывает список всех доступных команд."""
    help_text = (
        "📋 *Доступные команды:*\n\n"
        "*/start* - Приветственное сообщение от Ким\n"
        "_Начать работу с ассистентом_\n\n"
        "*/help* - Показать список всех команд\n"
        "_Это сообщение_\n\n"
        "*/reset* - Очистить контекст диалога\n"
        "_Начать разговор заново, забыв предыдущую историю_\n\n"
        "*/myid* - Показать ваш Chat ID\n"
        "_Используется для настройки уведомлений диагностики_\n\n"
        "💬 *Обычные сообщения* - Задать вопрос Ким\n"
        "_Просто отправьте текст, и Ким ответит, учитывая контекст всего разговора_\n\n"
        "💡 *Совет:* Используйте в запросе фразы типа \"режим качества\" или \"реши это GPT-5\", "
        "чтобы переключиться на более мощную модель для сложных задач."
    )
    
    await message.answer(help_text, parse_mode="Markdown")
    logger.info(f"Команда /help выполнена для пользователя {message.from_user.id}")


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    """Обработчик команды /myid — показывает Chat ID пользователя."""
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    
    response = f"Ваш Chat ID: `{chat_id}`"
    if user_id and user_id != chat_id:
        response += f"\nВаш User ID: `{user_id}`"
    
    response += "\n\nЭтот ID можно использовать для настройки ALERTS_CHAT_ID в .env"
    
    await message.answer(response, parse_mode="Markdown")
    logger.info(f"Команда /myid выполнена. Chat ID: {chat_id}, User ID: {user_id}")


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    """Обработчик команды /reset."""
    logger.info(f"Получена команда /reset от пользователя {message.from_user.id}")
    
    if _dialog_store is None:
        logger.error("Dialog store не инициализирован")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    user_id = message.from_user.id
    _dialog_store.reset(user_id)
    logger.info(f"Контекст диалога очищен для пользователя {user_id}")
    await message.answer("Контекст диалога очищен. Начинаем с чистого листа!")


@router.message(F.text)
async def handle_message(message: Message) -> None:
    """Обработчик текстовых сообщений."""
    # Пропускаем команды (они обрабатываются отдельными обработчиками)
    if message.text and message.text.startswith("/"):
        return
    
    user_id = message.from_user.id
    user_message = message.text or ""
    
    logger.info(f"Получено сообщение от пользователя {user_id}: {user_message[:50]}...")
    
    if _dialog_store is None or _llm_router is None:
        logger.error("Зависимости не инициализированы")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    if not user_message.strip():
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return

    # Показываем статус "печатает..."
    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        # Добавляем сообщение пользователя в историю
        _dialog_store.append_user_message(user_id, user_message)

        # Формируем список сообщений с системным промптом
        history = _dialog_store.get_history(user_id)
        messages = [get_system_prompt()] + history

        logger.debug(f"Отправка запроса в LLM для пользователя {user_id}, сообщений: {len(messages)}")

        # Получаем ответ от LLM
        response = await _llm_router.run(messages)

        logger.info(f"Получен ответ от LLM для пользователя {user_id}, длина: {len(response)}")

        # Добавляем ответ ассистента в историю
        _dialog_store.append_assistant_message(user_id, response)

        # Отправляем ответ пользователю
        await message.answer(response)

    except BudgetExceededError as e:
        logger.warning(f"Превышен лимит токенов для пользователя {user_id}: {e}")
        await message.answer(
            "Ким исчерпал дневной лимит запросов, попробуйте завтра."
        )

    except LLMError as e:
        logger.error(f"Ошибка LLM для пользователя {user_id}: {e}")
        await message.answer(
            "Ким сейчас не может ответить из-за ошибки, попробуйте позже."
        )

    except Exception as e:
        logger.exception(f"Неожиданная ошибка для пользователя {user_id}: {e}")
        await message.answer(
            "Ким сейчас не может ответить из-за ошибки, попробуйте позже."
        )

