"""Обработчики команд для управления напоминаниями."""

import re
from datetime import datetime
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from kim_core.logging import logger
from kim_scheduler.calendar.service import CalendarService

router = Router()

# Глобальная зависимость (устанавливается при инициализации бота)
_calendar_service: Optional[CalendarService] = None


def init_calendar_service(service: CalendarService) -> None:
    """
    Инициализирует сервис календаря для обработчиков.

    Args:
        service: Сервис календаря
    """
    global _calendar_service
    _calendar_service = service
    logger.info("CalendarService инициализирован для обработчиков напоминаний")


@router.message(Command("remind"))
async def cmd_remind(message: Message) -> None:
    """
    Обработчик команды /remind.

    Формат: /remind YYYY-MM-DD HH:MM Текст напоминания [минут_до]
    Примеры:
        /remind 2025-12-10 15:00 созвон с клиентом 30
        /remind 2025-12-10 09:00 выгулять собаку
    """
    if _calendar_service is None:
        logger.error("CalendarService не инициализирован")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    user_id = message.from_user.id
    command_text = message.text or ""

    # Парсим аргументы команды
    # Формат: /remind YYYY-MM-DD HH:MM текст [минут_до]
    match = re.match(
        r"/remind\s+(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})\s+(.+?)(?:\s+(\d+))?$",
        command_text,
    )

    if not match:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Используйте: `/remind YYYY-MM-DD HH:MM Текст напоминания [минут_до]`\n\n"
            "Примеры:\n"
            "• `/remind 2025-12-10 15:00 созвон с клиентом 30`\n"
            "• `/remind 2025-12-10 09:00 выгулять собаку`\n\n"
            "⚠️ Время указывается по UTC.",
            parse_mode="Markdown",
        )
        return

    date_str, hour_str, minute_str, title, minutes_before_str = match.groups()

    try:
        # Парсим дату и время (считаем их UTC)
        dt_naive = datetime.strptime(f"{date_str} {hour_str}:{minute_str}", "%Y-%m-%d %H:%M")
        # Явно указываем, что это UTC (naive datetime, но считаем его UTC)
        dt_utc = dt_naive.replace(tzinfo=None)  # Храним как naive, но подразумеваем UTC

        # Проверяем, что время в будущем
        if dt_utc <= datetime.utcnow():
            await message.answer("❌ Время события должно быть в будущем.")
            return

        # Парсим минут_до (по умолчанию 10)
        remind_before_minutes = int(minutes_before_str) if minutes_before_str else 10

        if remind_before_minutes < 0:
            await message.answer("❌ Количество минут до напоминания не может быть отрицательным.")
            return

        # Создаём событие
        event = _calendar_service.create_event(
            user_id=user_id,
            title=title.strip(),
            dt_utc=dt_utc,
            remind_before_minutes=remind_before_minutes,
        )

        # Форматируем ответ
        time_str = dt_utc.strftime("%Y-%m-%d %H:%M")
        response = (
            f"✅ Напоминание создано!\n\n"
            f"📌 ID: `{event.id}`\n"
            f"📅 Время: {time_str} UTC\n"
            f"📝 Текст: {event.title}\n"
            f"⏰ Напомнить за {remind_before_minutes} минут до события"
        )

        await message.answer(response, parse_mode="Markdown")
        logger.info(
            f"Напоминание создано: id={event.id}, user_id={user_id}, "
            f"datetime={time_str}, title={event.title[:50]}"
        )

    except ValueError as e:
        logger.error(f"Ошибка парсинга даты/времени: {e}")
        await message.answer(
            "❌ Ошибка: неверный формат даты или времени.\n\n"
            "Используйте формат: YYYY-MM-DD HH:MM\n"
            "Пример: 2025-12-10 15:00"
        )
    except Exception as e:
        logger.exception(f"Ошибка при создании напоминания: {e}")
        await message.answer("❌ Произошла ошибка при создании напоминания. Попробуйте позже.")


@router.message(Command("reminders"))
async def cmd_reminders(message: Message) -> None:
    """Обработчик команды /reminders — показывает список будущих напоминаний."""
    if _calendar_service is None:
        logger.error("CalendarService не инициализирован")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    user_id = message.from_user.id
    events = _calendar_service.list_events(user_id)

    if not events:
        await message.answer("📭 У вас пока нет запланированных напоминаний.")
        return

    # Форматируем список событий
    lines = ["📋 *Ваши напоминания:*\n"]
    for event in events:
        time_str = event.datetime_utc.strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"`{event.id}` | {time_str} UTC | {event.title} "
            f"(за {event.remind_before_minutes} мин до)"
        )

    response = "\n".join(lines)
    await message.answer(response, parse_mode="Markdown")
    logger.info(f"Список напоминаний показан: user_id={user_id}, событий={len(events)}")


@router.message(Command("remind_delete"))
async def cmd_remind_delete(message: Message) -> None:
    """
    Обработчик команды /remind_delete <id> — удаляет напоминание.

    Формат: /remind_delete <id>
    """
    if _calendar_service is None:
        logger.error("CalendarService не инициализирован")
        await message.answer("Ошибка инициализации. Попробуйте позже.")
        return

    user_id = message.from_user.id
    command_text = message.text or ""

    # Парсим ID
    parts = command_text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Используйте: `/remind_delete <id>`\n\n"
            "Пример: `/remind_delete 1`",
            parse_mode="Markdown",
        )
        return

    try:
        event_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    # Проверяем, есть ли такое событие у пользователя
    user_events = _calendar_service.list_events(user_id)
    event_exists = any(e.id == event_id for e in user_events)

    if not event_exists:
        await message.answer("❌ Событие с таким id не найдено.")
        return

    # Удаляем событие
    _calendar_service.delete_event(event_id, user_id)
    await message.answer(f"✅ Напоминание с ID `{event_id}` удалено.", parse_mode="Markdown")
    logger.info(f"Напоминание удалено: id={event_id}, user_id={user_id}")

