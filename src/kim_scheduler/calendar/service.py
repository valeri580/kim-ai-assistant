"""Сервис календаря для управления событиями."""

from datetime import datetime

from kim_core.logging import logger

from kim_scheduler.calendar.storage import CalendarEvent, CalendarStorage


class CalendarService:
    """Сервис для работы с календарём событий."""

    def __init__(self, storage: CalendarStorage) -> None:
        """
        Инициализирует сервис календаря.

        Args:
            storage: Хранилище событий
        """
        self.storage = storage
        logger.debug("CalendarService инициализирован")

    def create_event(
        self,
        user_id: int,
        title: str,
        dt_utc: datetime,
        remind_before_minutes: int,
    ) -> CalendarEvent:
        """
        Создаёт новое событие.

        Args:
            user_id: ID пользователя Telegram
            title: Название события
            dt_utc: Дата и время события (UTC)
            remind_before_minutes: За сколько минут до события напомнить

        Returns:
            Созданное событие с заполненным id
        """
        event = CalendarEvent(
            id=None,
            user_id=user_id,
            title=title,
            datetime_utc=dt_utc,
            remind_before_minutes=remind_before_minutes,
            created_at=datetime.utcnow(),
            is_fired=False,
        )
        result = self.storage.add_event(event)
        logger.info(f"Событие создано через CalendarService: id={result.id}, user_id={user_id}")
        return result

    def list_events(self, user_id: int) -> list[CalendarEvent]:
        """
        Возвращает список будущих событий пользователя.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Список будущих событий
        """
        return self.storage.list_upcoming(user_id)

    def delete_event(self, event_id: int, user_id: int) -> None:
        """
        Удаляет событие пользователя.

        Args:
            event_id: ID события
            user_id: ID пользователя Telegram
        """
        self.storage.delete_event(event_id, user_id)
        logger.info(f"Событие удалено через CalendarService: id={event_id}, user_id={user_id}")

    def get_due_events(self, now_utc: datetime) -> list[CalendarEvent]:
        """
        Возвращает события, для которых пора напомнить.

        Args:
            now_utc: Текущее время UTC

        Returns:
            Список событий, для которых пора напомнить
        """
        return self.storage.get_due_events(now_utc)

