"""Тестовый скрипт для проверки Vosk + микрофон без hotword.

Запускает простую петлю на 10–15 секунд, читает аудио с микрофона,
передаёт его в Vosk и выводит partial/final результаты.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import sounddevice as sd
import vosk
from dotenv import load_dotenv

from kim_core.config.settings import load_config
from kim_core.logging.setup import init_logger
from kim_core.logging import logger


SAMPLE_RATE = 16000
CHUNK_SIZE = 4000
TEST_DURATION_SECONDS = 15.0


def get_vosk_model_path() -> str:
    """Получает путь к модели Vosk из .env или значения по умолчанию."""
    load_dotenv()
    model_path = os.getenv("VOSK_MODEL_PATH")

    if model_path:
        return model_path

    # Значение по умолчанию, как в голосовом ассистенте
    return "models/vosk-ru"


def main() -> None:
    """Запуск теста Vosk + микрофон."""
    # Загружаем конфиг и логер для консистентности с проектом
    config = load_config()
    init_logger(config)

    logger.info("=" * 60)
    logger.info("Тест Vosk + микрофон (без hotword)")
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

    # Загрузка модели
    try:
        logger.info("Загрузка модели Vosk...")
        model = vosk.Model(model_path)
        logger.info("Модель Vosk загружена успешно")
    except Exception as e:
        logger.error(f"Ошибка загрузки модели Vosk: {e}")
        return

    # Инициализация распознавателя
    try:
        rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
        rec.SetWords(True)
        logger.info(
            f"Инициализирован KaldiRecognizer: sample_rate={SAMPLE_RATE}, "
            f"chunk_size={CHUNK_SIZE}"
        )
    except Exception as e:
        logger.error(f"Ошибка инициализации KaldiRecognizer: {e}")
        return

    # Информация по устройству ввода
    try:
        default_input = sd.default.device[0]
        logger.info(f"Устройство ввода по умолчанию: {default_input}")
    except Exception as e:
        logger.warning(f"Не удалось определить устройство ввода: {e}")

    print(
        "\nГоворите в микрофон (тест ~15 секунд)...\n"
        "В stdout и логах будут отображаться partial/final результаты.\n"
    )

    start_time = time.time()

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=CHUNK_SIZE,
            dtype="int16",
            channels=1,
        ) as stream:
            logger.info("Микрофон открыт для теста Vosk")

            while True:
                now = time.time()
                if now - start_time >= TEST_DURATION_SECONDS:
                    logger.info("Тест завершён по таймеру")
                    break

                try:
                    data, _ = stream.read(CHUNK_SIZE)
                except Exception as e:
                    logger.error(f"Ошибка чтения аудио из микрофона: {e}")
                    break

                if data is None or len(data) == 0:
                    logger.debug("Vosk test: пустой аудио-чанк, пропускаем")
                    continue

                data_bytes = data.tobytes()

                # Обработка через Vosk
                try:
                    if rec.AcceptWaveform(data_bytes):
                        result_str = rec.Result()
                        logger.debug(f"Vosk test: final JSON = {result_str}")
                        result = json.loads(result_str)
                        text = result.get("text", "").strip()
                        print(f"[FINAL] {text}")
                        logger.info(f"Vosk test: final='{text}'")
                    else:
                        partial_str = rec.PartialResult()
                        if partial_str:
                            result = json.loads(partial_str)
                            partial = result.get("partial", "").strip()
                            if partial:
                                print(f"[PARTIAL] {partial}")
                                logger.info(f"Vosk test: partial='{partial}'")
                except Exception as e:
                    logger.error(f"Ошибка обработки аудио в Vosk: {e}")
                    continue

    except KeyboardInterrupt:
        logger.info("Тест Vosk прерван пользователем (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Критическая ошибка в тесте Vosk: {e}")

    logger.info("Тест Vosk + микрофон завершён")


if __name__ == "__main__":
    main()


