"""Хранилище событий календаря в SQLite."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from kim_core.logging import logger


@dataclass
class CalendarEvent:
    """Модель события календаря."""

    id: Optional[int]
    user_id: int  # Telegram user id
    title: str
    datetime_utc: datetime
    remind_before_minutes: int
    created_at: datetime
    is_fired: bool = False


class CalendarStorage:
    """Хранилище событий календаря в SQLite."""

    def __init__(self, db_path: str) -> None:
        """
        Инициализирует хранилище.

        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = Path(db_path)
        # Создаём директорию, если её нет
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"CalendarStorage инициализирован: {self.db_path}")

    def _init_db(self) -> None:
        """Создаёт таблицу events, если её нет."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    datetime_utc TEXT NOT NULL,
                    remind_before_minutes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    is_fired INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()
            logger.debug("Таблица events проверена/создана")

    def add_event(self, event: CalendarEvent) -> CalendarEvent:
        """
        Добавляет событие в БД и возвращает его с заполненным id.

        Args:
            event: Событие для добавления

        Returns:
            Событие с заполненным id
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (user_id, title, datetime_utc, remind_before_minutes, created_at, is_fired)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.user_id,
                    event.title,
                    event.datetime_utc.isoformat(),
                    event.remind_before_minutes,
                    event.created_at.isoformat(),
                    1 if event.is_fired else 0,
                ),
            )
            conn.commit()
            event_id = cursor.lastrowid
            logger.info(f"Событие добавлено: id={event_id}, user_id={event.user_id}, title={event.title[:50]}")
            return CalendarEvent(
                id=event_id,
                user_id=event.user_id,
                title=event.title,
                datetime_utc=event.datetime_utc,
                remind_before_minutes=event.remind_before_minutes,
                created_at=event.created_at,
                is_fired=event.is_fired,
            )

    def list_upcoming(self, user_id: int, limit: int = 20) -> list[CalendarEvent]:
        """
        Возвращает будущие события пользователя.

        Args:
            user_id: ID пользователя Telegram
            limit: Максимальное количество событий

        Returns:
            Список будущих событий
        """
        now_utc = datetime.utcnow()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, user_id, title, datetime_utc, remind_before_minutes, created_at, is_fired
                FROM events
                WHERE user_id = ? AND is_fired = 0 AND datetime_utc >= ?
                ORDER BY datetime_utc ASC
                LIMIT ?
                """,
                (user_id, now_utc.isoformat(), limit),
            ).fetchall()

            events = []
            for row in rows:
                events.append(
                    CalendarEvent(
                        id=row["id"],
                        user_id=row["user_id"],
                        title=row["title"],
                        datetime_utc=datetime.fromisoformat(row["datetime_utc"]),
                        remind_before_minutes=row["remind_before_minutes"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        is_fired=bool(row["is_fired"]),
                    )
                )

            logger.debug(f"Найдено {len(events)} будущих событий для user_id={user_id}")
            return events

    def delete_event(self, event_id: int, user_id: int) -> None:
        """
        Удаляет событие только этого пользователя.

        Args:
            event_id: ID события
            user_id: ID пользователя Telegram
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM events
                WHERE id = ? AND user_id = ?
                """,
                (event_id, user_id),
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Событие удалено: id={event_id}, user_id={user_id}")
            else:
                logger.warning(f"Событие не найдено для удаления: id={event_id}, user_id={user_id}")

    def mark_fired(self, event_id: int) -> None:
        """
        Помечает событие как выполненное (is_fired=True).

        Args:
            event_id: ID события
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE events
                SET is_fired = 1
                WHERE id = ?
                """,
                (event_id,),
            )
            conn.commit()
            logger.debug(f"Событие помечено как fired: id={event_id}")

    def get_due_events(self, now_utc: datetime) -> list[CalendarEvent]:
        """
        Выбирает события, для которых пора напомнить.

        Условие: datetime_utc - remind_before_minutes * 60 <= now_utc <= datetime_utc

        Args:
            now_utc: Текущее время UTC

        Returns:
            Список событий, для которых пора напомнить
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, user_id, title, datetime_utc, remind_before_minutes, created_at, is_fired
                FROM events
                WHERE is_fired = 0
                ORDER BY datetime_utc ASC
                """
            ).fetchall()

            due_events = []
            for row in rows:
                event_datetime = datetime.fromisoformat(row["datetime_utc"])
                remind_before_seconds = row["remind_before_minutes"] * 60
                remind_start = event_datetime.timestamp() - remind_before_seconds
                now_timestamp = now_utc.timestamp()
                event_timestamp = event_datetime.timestamp()

                # Проверяем: remind_start <= now <= event_datetime
                if remind_start <= now_timestamp <= event_timestamp:
                    due_events.append(
                        CalendarEvent(
                            id=row["id"],
                            user_id=row["user_id"],
                            title=row["title"],
                            datetime_utc=event_datetime,
                            remind_before_minutes=row["remind_before_minutes"],
                            created_at=datetime.fromisoformat(row["created_at"]),
                            is_fired=bool(row["is_fired"]),
                        )
                    )

            logger.debug(f"Найдено {len(due_events)} событий для напоминания")
            return due_events

