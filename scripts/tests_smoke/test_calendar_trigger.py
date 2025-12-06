"""Smoke-тест для проверки календаря и напоминаний."""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger, logger
from kim_scheduler.calendar.service import CalendarService
from kim_scheduler.calendar.storage import CalendarStorage


def test_calendar_trigger() -> bool:
    """
    Проверяет, что календарь может создать и получить напоминание.

    Returns:
        bool: True если календарь работает корректно
    """
    try:
        # Инициализация логирования
        config = load_config()
        init_logger(config)
        
        logger.info("=" * 60)
        logger.info("Smoke test: Calendar & Reminders")
        logger.info("=" * 60)
        
        # Создание сервиса календаря
        try:
            db_path = config.reminders_db_path if hasattr(config, 'reminders_db_path') else "data/calendar.db"
            storage = CalendarStorage(db_path)
            service = CalendarService(storage)
            
            logger.info("✓ CalendarService инициализирован")
            
            # Ждём немного
            time.sleep(1)
            
            # Создаём тестовое событие
            test_user_id = 999999  # Тестовый ID
            test_title = "Smoke test reminder"
            test_datetime = datetime.utcnow() + timedelta(hours=1)
            test_remind_before = 30
            
            logger.info("Создание тестового напоминания...")
            event = service.create_event(
                user_id=test_user_id,
                title=test_title,
                dt_utc=test_datetime,
                remind_before_minutes=test_remind_before,
            )
            
            if not event or not event.id:
                logger.error("❌ Не удалось создать событие")
                return False
            
            logger.info(f"✓ Событие создано: id={event.id}, title='{event.title}'")
            
            # Проверяем, что событие можно получить
            time.sleep(1)
            
            events = service.list_events(test_user_id)
            found_event = next((e for e in events if e.id == event.id), None)
            
            if not found_event:
                logger.error("❌ Созданное событие не найдено в списке")
                return False
            
            logger.info(f"✓ Событие найдено в списке: id={found_event.id}")
            
            # Проверяем get_due_events (для события в будущем не должно быть due)
            due_events = service.get_due_events(datetime.utcnow())
            logger.info(f"✓ Проверка due_events выполнена: найдено {len(due_events)} событий")
            
            # Удаляем тестовое событие
            service.delete_event(event.id, test_user_id)
            logger.info("✓ Тестовое событие удалено")
            
            logger.info("✅ Calendar trigger test: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке календаря: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_calendar_trigger()
    sys.exit(0 if success else 1)

