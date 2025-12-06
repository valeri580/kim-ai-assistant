"""Сервис диагностики системы с периодической проверкой и уведомлениями."""

import asyncio
import sys
from pathlib import Path

# Добавляем src в путь для импорта модулей
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.config.runtime import RuntimeSettingsStore, merge_config_with_runtime
from kim_core.logging import init_logger, logger
from kim_desktop.diagnostics.system_info import (
    Thresholds,
    check_thresholds,
    format_telegram_message,
    format_voice_message,
    get_metrics,
)
from kim_telegram.notify import TelegramNotifier


async def main() -> None:
    """Основная функция сервиса диагностики."""
    # Загрузка базовой конфигурации
    base_config = load_config()

    # Инициализация логирования
    init_logger(base_config)

    # Загрузка runtime-настроек и объединение с базовой конфигурацией
    import os
    settings_path = os.getenv("RUNTIME_SETTINGS_PATH", "data/runtime_settings.json")
    runtime_store = RuntimeSettingsStore(settings_path)
    runtime_settings = runtime_store.load()
    merged_config = merge_config_with_runtime(base_config, runtime_settings)

    logger.info("=" * 60)
    logger.info("Запуск сервиса диагностики системы")
    logger.info("=" * 60)

    # Создание порогов из объединённой конфигурации (runtime overrides)
    thresholds = Thresholds(
        cpu_warn=merged_config.cpu_warn,
        ram_warn=merged_config.ram_warn,
        disk_warn=merged_config.disk_warn,
        temp_warn=merged_config.temp_warn,
    )

    logger.info(f"Пороги: CPU={thresholds.cpu_warn}%, RAM={thresholds.ram_warn}%, "
                f"Диск={thresholds.disk_warn}%, "
                f"Температура={'не задана' if thresholds.temp_warn is None else f'{thresholds.temp_warn}°C'}")

    # Инициализация Telegram уведомителя
    telegram_notifier: TelegramNotifier | None = None

    if merged_config.alerts_chat_id is None:
        logger.warning(
            "ALERTS_CHAT_ID не задан в конфигурации. "
            "Уведомления в Telegram отключены. "
            "Голосовые уведомления всё ещё доступны, если голосовой ассистент запущен."
        )
    elif not merged_config.telegram_bot_token:
        logger.warning(
            "BOT_TOKEN не задан. Уведомления в Telegram недоступны. "
            "Голосовые уведомления всё ещё доступны, если голосовой ассистент запущен."
        )
    else:
        try:
            telegram_notifier = TelegramNotifier(
                bot_token=merged_config.telegram_bot_token,
                chat_id=merged_config.alerts_chat_id,
            )
            logger.info(f"Telegram уведомления включены для chat_id={merged_config.alerts_chat_id}")
        except Exception as e:
            logger.error(f"Ошибка инициализации TelegramNotifier: {e}")

    # Попытка инициализации голосовых уведомлений
    voice = None
    try:
        from kim_voice.tts.voice import KimVoice

        voice = KimVoice(rate=170, volume=1.0)
        logger.info("Голосовые уведомления доступны")
    except ImportError:
        logger.info("Голосовые уведомления недоступны (модуль kim_voice не найден)")
    except Exception as e:
        logger.warning(f"Ошибка инициализации голосовых уведомлений: {e}")

    if not telegram_notifier and not voice:
        logger.error(
            "Нет доступных способов уведомления. "
            "Необходимо указать ALERTS_CHAT_ID и BOT_TOKEN для Telegram уведомлений "
            "или запустить голосовой ассистент для голосовых уведомлений."
        )
        logger.info("Сервис завершает работу")
        return

    interval = merged_config.diagnostics_interval_seconds
    logger.info(f"Интервал проверки: {interval} секунд")
    logger.info("Сервис диагностики запущен. Для остановки нажмите Ctrl+C")
    logger.info("=" * 60)

    try:
        while True:
            # Проверяем, изменились ли runtime-настройки
            new_runtime_settings = runtime_store.reload_if_changed()
            if new_runtime_settings is not None:
                merged_config = merge_config_with_runtime(base_config, new_runtime_settings)
                thresholds = Thresholds(
                    cpu_warn=merged_config.cpu_warn,
                    ram_warn=merged_config.ram_warn,
                    disk_warn=merged_config.disk_warn,
                    temp_warn=merged_config.temp_warn,
                )
                logger.info(f"Пороги обновлены: CPU={thresholds.cpu_warn}%, RAM={thresholds.ram_warn}%, "
                           f"Диск={thresholds.disk_warn}%, "
                           f"Температура={'не задана' if thresholds.temp_warn is None else f'{thresholds.temp_warn}°C'}")

            # Сбор метрик
            metrics = get_metrics()

            # Проверка порогов и генерация рекомендаций
            warnings, recommendations = check_thresholds(metrics, thresholds)

            if warnings:
                logger.warning(f"Обнаружены проблемы: {len(warnings)} предупреждений, {len(recommendations)} рекомендаций")

                # Отправка в Telegram с Markdown форматированием
                if telegram_notifier:
                    try:
                        telegram_message = format_telegram_message(warnings, recommendations)
                        await telegram_notifier.send_alert(telegram_message, parse_mode="Markdown")
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления в Telegram: {e}")

                # Голосовое уведомление (краткие фразы)
                if voice:
                    try:
                        voice_message = format_voice_message(warnings, recommendations)
                        voice.speak(voice_message)
                    except Exception as e:
                        logger.warning(f"Ошибка голосового уведомления: {e}")
            else:
                logger.debug("Все метрики в норме")

            # Ожидание до следующей проверки
            await asyncio.sleep(interval)

    except KeyboardInterrupt:
        logger.info("\nПолучен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.exception(f"Критическая ошибка в сервисе диагностики: {e}")
    finally:
        # Закрытие ресурсов
        if telegram_notifier:
            await telegram_notifier.close()
        logger.info("Сервис диагностики остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nОстановка сервиса диагностики...")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)

