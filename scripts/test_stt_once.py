"""Тестовый скрипт для проверки STT (распознавание одной фразы).

Тестирует модуль KimSTT с фильтрами по длине фразы и уверенности.
Использует тот же код, что и основной ассистент.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv

from kim_core.config.settings import load_config
from kim_core.logging.setup import init_logger
from kim_core.logging import logger
from kim_voice.stt.speech_to_text import KimSTT, STTConfig


def get_vosk_model_path() -> str:
    """Получает путь к модели Vosk из .env или значения по умолчанию."""
    load_dotenv()
    model_path = os.getenv("VOSK_MODEL_PATH")

    if model_path:
        return model_path

    # Значение по умолчанию, как в голосовом ассистенте
    return "models/vosk-ru"


def main() -> None:
    """Запуск теста STT."""
    # Загружаем конфиг и логер для консистентности с проектом
    config = load_config()
    init_logger(config)

    logger.info("=" * 60)
    logger.info("Тест STT (распознавание одной фразы)")
    logger.info("=" * 60)

    model_path = get_vosk_model_path()
    logger.info(f"Используется модель Vosk: {model_path}")

    if not os.path.exists(model_path):
        logger.error(f"Модель Vosk не найдена по пути: {model_path}")
        print(
            f"\n❌ Модель Vosk не найдена по пути: {model_path}\n"
            f"Проверьте VOSK_MODEL_PATH в .env или установку модели.\n"
        )
        return

    # Загружаем настройки VAD из переменных окружения
    load_dotenv()
    stt_use_vad = os.getenv("STT_USE_VAD", "0").lower() in ("1", "true", "yes", "on")
    stt_vad_aggressiveness = int(os.getenv("STT_VAD_AGGRESSIVENESS", "2"))

    # Создание конфигурации STT с теми же параметрами, что в основном приложении
    stt_config = STTConfig(
        model_path=model_path,
        sample_rate=config.mic_sample_rate,
        chunk_size=config.mic_chunk_size,
        max_phrase_duration=10.0,
        silence_timeout=1.5,
        min_phrase_chars=5,
        min_avg_confidence=0.6,
        debug_log_words=False,
        use_vad=stt_use_vad,
        vad_aggressiveness=stt_vad_aggressiveness,
        device_index=config.mic_device_index,
    )

    # Выводим текущие настройки
    print("\n" + "=" * 60)
    print("Текущие настройки STT:")
    print("=" * 60)
    print(f"  Модель: {model_path}")
    print(f"  Частота дискретизации: {stt_config.sample_rate} Hz")
    print(f"  Размер блока: {stt_config.chunk_size} сэмплов")
    print(f"  Минимальная длина фразы: {stt_config.min_phrase_chars} символов")
    print(f"  Минимальная уверенность: {stt_config.min_avg_confidence}")
    print(f"  VAD включён: {stt_config.use_vad}")
    if stt_config.use_vad:
        print(f"  Агрессивность VAD: {stt_config.vad_aggressiveness}")
    if stt_config.device_index is not None:
        print(f"  Устройство ввода (индекс): {stt_config.device_index}")
    else:
        print(f"  Устройство ввода: по умолчанию")
    print("=" * 60 + "\n")

    logger.info(f"STT конфигурация: min_phrase_chars={stt_config.min_phrase_chars}, "
                f"min_avg_confidence={stt_config.min_avg_confidence}, "
                f"use_vad={stt_config.use_vad}")

    # Создание распознавателя речи
    try:
        logger.info("Инициализация распознавателя речи (STT)...")
        stt = KimSTT(stt_config)
        logger.info("STT инициализирован успешно")
    except Exception as e:
        logger.error(f"Ошибка инициализации STT: {e}")
        print(f"\n❌ Ошибка инициализации STT: {e}\n")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 60)
    print("ГОТОВ К ПРОСЛУШИВАНИЮ")
    print("=" * 60)
    print("\nПроизнесите ОДНУ фразу в микрофон.")
    print("После окончания фразы (пауза ~1.5 сек) результат будет распознан.")
    print("\nПримеры фраз для тестирования:")
    print("  - Короткая, чёткая: 'Привет, Ким'")
    print("  - Средняя: 'Расскажи анекдот'")
    print("  - Длинная: 'Ким, сделай мне напоминание на завтра в восемь утра'")
    print("\nДля остановки нажмите Ctrl+C\n")

    try:
        # Используем listen_once_with_confidence для получения текста и уверенности
        result = stt.listen_once_with_confidence()

        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ")
        print("=" * 60)

        if result is None:
            print("\n❌ Фраза не была распознана или не прошла фильтры.")
            print("\nВозможные причины:")
            print("  - Фраза слишком короткая (< 5 символов)")
            print("  - Низкая уверенность распознавания (< 0.6)")
            print("  - Речь не была обнаружена")
            print("\nПроверьте логи для детальной информации.\n")
            logger.warning("STT тест: фраза не распознана или отфильтрована")
        else:
            text, avg_conf = result
            print(f"\n✓ Текст: '{text}'")
            print(f"✓ Уверенность: {avg_conf:.2f}")
            print(f"✓ Длина: {len(text)} символов")
            
            # Проверяем, прошла ли фраза все фильтры
            if len(text) >= stt_config.min_phrase_chars:
                print(f"✓ Длина прошла фильтр (≥ {stt_config.min_phrase_chars} символов)")
            else:
                print(f"⚠ Длина не прошла фильтр (требуется ≥ {stt_config.min_phrase_chars} символов)")
            
            if avg_conf >= stt_config.min_avg_confidence:
                print(f"✓ Уверенность прошла фильтр (≥ {stt_config.min_avg_confidence})")
            else:
                print(f"⚠ Уверенность не прошла фильтр (требуется ≥ {stt_config.min_avg_confidence})")
            
            print("\n")
            logger.info(f"STT тест: успешно распознано '{text}' с уверенностью {avg_conf:.2f}")

    except KeyboardInterrupt:
        logger.info("Тест STT прерван пользователем (KeyboardInterrupt)")
        print("\n\nТест прерван пользователем.\n")
    except Exception as e:
        logger.error(f"Критическая ошибка в тесте STT: {e}")
        print(f"\n❌ Ошибка: {e}\n")
        import traceback
        traceback.print_exc()

    logger.info("Тест STT завершён")


if __name__ == "__main__":
    main()

