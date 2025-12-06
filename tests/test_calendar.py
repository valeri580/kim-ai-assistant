"""Тесты для модуля календаря и напоминаний."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from kim_scheduler.calendar.service import CalendarService
from kim_scheduler.calendar.storage import CalendarEvent, CalendarStorage


@pytest.fixture
def temp_db():
    """Создаёт временную БД для тестов."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Удаляем временный файл после теста
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def storage(temp_db):
    """Создаёт CalendarStorage с временной БД."""
    return CalendarStorage(temp_db)


@pytest.fixture
def service(storage):
    """Создаёт CalendarService."""
    return CalendarService(storage)


def test_create_event(service):
    """Тест: создание напоминания."""
    user_id = 12345
    title = "Тестовое напоминание"
    dt_utc = datetime.utcnow() + timedelta(hours=1)
    remind_before_minutes = 10

    event = service.create_event(
        user_id=user_id,
        title=title,
        dt_utc=dt_utc,
        remind_before_minutes=remind_before_minutes,
    )

    assert event.id is not None
    assert event.user_id == user_id
    assert event.title == title
    assert event.datetime_utc == dt_utc
    assert event.remind_before_minutes == remind_before_minutes
    assert event.is_fired is False


def test_list_events(service):
    """Тест: вывод списка напоминаний."""
    user_id = 12345

    # Создаём несколько событий
    now = datetime.utcnow()
    event1 = service.create_event(
        user_id=user_id,
        title="Событие 1",
        dt_utc=now + timedelta(hours=1),
        remind_before_minutes=10,
    )
    event2 = service.create_event(
        user_id=user_id,
        title="Событие 2",
        dt_utc=now + timedelta(hours=2),
        remind_before_minutes=15,
    )
    # Событие в прошлом (не должно попасть в список)
    service.create_event(
        user_id=user_id,
        title="Прошлое событие",
        dt_utc=now - timedelta(hours=1),
        remind_before_minutes=10,
    )

    events = service.list_events(user_id)

    assert len(events) == 2
    assert events[0].id == event1.id
    assert events[1].id == event2.id
    # Проверяем, что события отсортированы по времени
    assert events[0].datetime_utc < events[1].datetime_utc


def test_list_events_empty(service):
    """Тест: список пуст, если нет событий."""
    user_id = 12345
    events = service.list_events(user_id)
    assert len(events) == 0


def test_list_events_different_users(service):
    """Тест: пользователи видят только свои события."""
    user1_id = 11111
    user2_id = 22222

    # Создаём события для разных пользователей
    now = datetime.utcnow()
    service.create_event(
        user_id=user1_id,
        title="Событие пользователя 1",
        dt_utc=now + timedelta(hours=1),
        remind_before_minutes=10,
    )
    service.create_event(
        user_id=user2_id,
        title="Событие пользователя 2",
        dt_utc=now + timedelta(hours=1),
        remind_before_minutes=10,
    )

    events_user1 = service.list_events(user1_id)
    events_user2 = service.list_events(user2_id)

    assert len(events_user1) == 1
    assert len(events_user2) == 1
    assert events_user1[0].user_id == user1_id
    assert events_user2[0].user_id == user2_id


def test_delete_event(service):
    """Тест: удаление напоминания."""
    user_id = 12345
    now = datetime.utcnow()

    event = service.create_event(
        user_id=user_id,
        title="Событие для удаления",
        dt_utc=now + timedelta(hours=1),
        remind_before_minutes=10,
    )

    # Проверяем, что событие есть
    events_before = service.list_events(user_id)
    assert len(events_before) == 1

    # Удаляем событие
    service.delete_event(event.id, user_id)

    # Проверяем, что события нет
    events_after = service.list_events(user_id)
    assert len(events_after) == 0


def test_delete_event_wrong_user(service):
    """Тест: нельзя удалить событие другого пользователя."""
    user1_id = 11111
    user2_id = 22222
    now = datetime.utcnow()

    event = service.create_event(
        user_id=user1_id,
        title="Событие пользователя 1",
        dt_utc=now + timedelta(hours=1),
        remind_before_minutes=10,
    )

    # Пытаемся удалить событие пользователя 1 от имени пользователя 2
    service.delete_event(event.id, user2_id)

    # Событие должно остаться
    events = service.list_events(user1_id)
    assert len(events) == 1


def test_get_due_events(service):
    """Тест: проверка триггера напоминаний."""
    user_id = 12345
    now = datetime.utcnow()

    # Событие, для которого пора напомнить (время напоминания уже прошло, но событие ещё не наступило)
    event_due = service.create_event(
        user_id=user_id,
        title="Событие для напоминания",
        dt_utc=now + timedelta(minutes=5),  # Событие через 5 минут
        remind_before_minutes=10,  # Напомнить за 10 минут
    )

    # Событие, для которого ещё рано напоминать
    service.create_event(
        user_id=user_id,
        title="Событие в будущем",
        dt_utc=now + timedelta(hours=2),
        remind_before_minutes=10,
    )

    # Событие, которое уже прошло
    service.create_event(
        user_id=user_id,
        title="Прошедшее событие",
        dt_utc=now - timedelta(hours=1),
        remind_before_minutes=10,
    )

    # Получаем события, для которых пора напомнить
    # Используем время, которое попадает в интервал напоминания
    check_time = now + timedelta(minutes=3)  # Между remind_start и event_time
    due_events = service.get_due_events(check_time)

    # Должно быть одно событие для напоминания
    assert len(due_events) == 1
    assert due_events[0].id == event_due.id
    assert due_events[0].title == "Событие для напоминания"


def test_get_due_events_not_yet(service):
    """Тест: событие ещё не готово для напоминания."""
    user_id = 12345
    now = datetime.utcnow()

    # Событие в будущем, для которого ещё рано напоминать
    service.create_event(
        user_id=user_id,
        title="Событие в будущем",
        dt_utc=now + timedelta(hours=2),
        remind_before_minutes=10,
    )

    # Проверяем сейчас (ещё рано напоминать)
    due_events = service.get_due_events(now)

    assert len(due_events) == 0


def test_get_due_events_already_passed(service):
    """Тест: событие уже прошло, напоминать не нужно."""
    user_id = 12345
    now = datetime.utcnow()

    # Событие в прошлом
    service.create_event(
        user_id=user_id,
        title="Прошедшее событие",
        dt_utc=now - timedelta(hours=1),
        remind_before_minutes=10,
    )

    # Проверяем сейчас (событие уже прошло)
    due_events = service.get_due_events(now)

    assert len(due_events) == 0

