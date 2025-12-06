"""Фоновый воркер для отправки напоминаний."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Добавляем src в путь для импорта модулей
project_root = Path(__file__).parent.parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger, logger
from kim_scheduler.calendar.service import CalendarService
from kim_scheduler.calendar.storage import CalendarStorage
from kim_telegram.notify import TelegramNotifier


async def send_notification(
    notifier: TelegramNotifier, user_id: int, event_title: str, event_datetime: datetime
) -> None:
    """
    Отправляет уведомление пользователю в Telegram.

    Args:
        notifier: TelegramNotifier для отправки сообщений
        user_id: ID пользователя Telegram
        event_title: Название события
        event_datetime: Дата и время события
    """
    time_str = event_datetime.strftime("%Y-%m-%d %H:%M")
    message = f"⏰ Напоминание: {event_title}\n📅 Время: {time_str} UTC"

    try:
        await notifier.send_message_to_user(user_id, message)
        logger.info(f"Напоминание отправлено: user_id={user_id}, title={event_title[:50]}")
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания user_id={user_id}: {e}")


async def try_voice_notification(title: str) -> None:
    """
    Пытается отправить голосовое уведомление (опционально).

    Args:
        title: Название события
    """
    try:
        from kim_voice.tts.voice import KimVoice

        voice = KimVoice(rate=170, volume=1.0)
        voice.speak(f"Напоминание: {title}")
        logger.debug(f"Голосовое напоминание озвучено: {title[:50]}")
    except ImportError:
        logger.debug("Голосовые уведомления недоступны (модуль kim_voice не найден)")
    except Exception as e:
        logger.warning(f"Ошибка голосового уведомления: {e}")


async def run_worker() -> None:
    """Основная функция воркера напоминаний."""
    # Загрузка конфигурации
    config = load_config()

    # Инициализация логирования
    init_logger(config)

    logger.info("=" * 60)
    logger.info("Запуск воркера напоминаний")
    logger.info("=" * 60)

    # Проверка наличия токена бота
    if not config.telegram_bot_token:
        logger.error("BOT_TOKEN не установлен в конфигурации. Воркер завершает работу.")
        return

    # Создание хранилища и сервиса календаря
    db_path = config.reminders_db_path
    storage = CalendarStorage(db_path)
    service = CalendarService(storage)
    logger.info(f"CalendarService инициализирован: db_path={db_path}")

    # Создание TelegramNotifier
    # Для воркера нужно отправлять сообщения конкретным пользователям,
    # поэтому создаём бота напрямую для отправки сообщений
    notifier = TelegramNotifier(
        bot_token=config.telegram_bot_token,
        chat_id=0,  # Будем отправлять напрямую по user_id
    )

    interval = config.reminders_interval_seconds
    logger.info(f"Интервал проверки: {interval} секунд")
    logger.info("Воркер напоминаний запущен. Для остановки нажмите Ctrl+C")
    logger.info("=" * 60)

    try:
        while True:
            # Получаем текущее время UTC
            now_utc = datetime.utcnow()

            # Получаем события, для которых пора напомнить
            due_events = service.get_due_events(now_utc)

            if due_events:
                logger.info(f"Найдено {len(due_events)} событий для напоминания")

            # Обрабатываем каждое событие
            for event in due_events:
                try:
                    # Отправляем уведомление в Telegram
                    await send_notification(
                        notifier, event.user_id, event.title, event.datetime_utc
                    )

                    # Помечаем событие как fired
                    storage.mark_fired(event.id)

                    # Опциональное голосовое уведомление
                    await try_voice_notification(event.title)

                    # Небольшая задержка между событиями
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Ошибка обработки события id={event.id}: {e}")
                    # Продолжаем обработку следующих событий

            # Ожидание до следующей проверки
            await asyncio.sleep(interval)

    except KeyboardInterrupt:
        logger.info("\nПолучен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.exception(f"Критическая ошибка в воркере напоминаний: {e}")
    finally:
        # Закрытие ресурсов
        await notifier.close()
        logger.info("Воркер напоминаний остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\nОстановка воркера напоминаний...")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)

