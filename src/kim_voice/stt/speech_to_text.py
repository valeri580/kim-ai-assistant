"""Модуль распознавания речи (STT) через Vosk."""

import json
import os
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import sounddevice as sd
import vosk

from kim_core.logging import logger

# Опциональный импорт WebRTC VAD
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    webrtcvad = None


class OptionalVAD:
    """
    Опциональная обёртка над WebRTC VAD для определения наличия речи в аудио.
    
    Если VAD недоступен или отключён, всегда возвращает True (пропускает всё).
    """
    
    def __init__(self, enabled: bool, aggressiveness: int = 2, sample_rate: int = 16000):
        """
        Инициализирует VAD.
        
        Args:
            enabled: Включить ли VAD
            aggressiveness: Агрессивность (0-3), где 3 - самая агрессивная
            sample_rate: Частота дискретизации аудио
        """
        self.enabled = enabled
        self.sample_rate = sample_rate
        self.vad = None
        
        if enabled and VAD_AVAILABLE:
            try:
                self.vad = webrtcvad.Vad(aggressiveness)
                logger.info(f"WebRTC VAD инициализирован (aggressiveness={aggressiveness})")
            except Exception as e:
                logger.warning(f"Не удалось инициализировать VAD: {e}, продолжаем без VAD")
                self.enabled = False
        elif enabled and not VAD_AVAILABLE:
            logger.warning("WebRTC VAD запрошен, но библиотека webrtcvad не установлена. "
                          "Установите: pip install webrtcvad")
            self.enabled = False
    
    def is_speech(self, frame_bytes: bytes) -> bool:
        """
        Проверяет, содержит ли аудиофрейм речь.
        
        Args:
            frame_bytes: Аудиофрейм в формате bytes
            
        Returns:
            bool: True если речь обнаружена, иначе False. Если VAD отключён - всегда True.
        """
        if not self.enabled or not self.vad:
            return True  # Пропускаем всё, если VAD не используется
        
        try:
            # WebRTC VAD требует фреймы определённой длины:
            # для 8kHz: 80, 160, 240 байт (10, 20, 30 мс)
            # для 16kHz: 160, 320, 480 байт (10, 20, 30 мс)
            # для 32kHz: 320, 640, 960 байт (10, 20, 30 мс)
            
            frame_length_ms = (len(frame_bytes) * 1000) // (self.sample_rate * 2)  # * 2 для int16
            
            # Поддерживаем только стандартные длины фреймов
            if frame_length_ms not in [10, 20, 30]:
                # Если фрейм неподходящего размера, пропускаем проверку
                return True
            
            return self.vad.is_speech(frame_bytes, self.sample_rate)
        except Exception as e:
            logger.debug(f"Ошибка VAD проверки: {e}, считаем что это речь")
            return True  # При ошибке пропускаем фрейм


@dataclass
class STTConfig:
    """Конфигурация распознавания речи."""

    model_path: str  # путь к модели Vosk
    sample_rate: int = 16000
    chunk_size: int = 4000
    max_phrase_duration: float = 10.0  # максимальная длительность одной фразы, сек
    silence_timeout: float = 1.5  # сколько секунд тишины считать концом фразы
    min_phrase_chars: int = 5  # минимальная длина распознанной фразы (в символах)
    min_avg_confidence: float = 0.6  # минимальная средняя уверенность по словам
    debug_log_words: bool = False  # если True — логировать по словам с конфиденсами
    use_vad: bool = False  # использовать WebRTC VAD для шумоподавления
    vad_aggressiveness: int = 2  # агрессивность VAD (0-3, где 3 - самая агрессивная)
    device_index: Optional[int] = None  # индекс устройства ввода (микрофон), None = по умолчанию


class KimSTT:
    """Класс для распознавания речи через Vosk."""

    def __init__(self, config: STTConfig) -> None:
        """
        Инициализирует распознаватель речи.

        Args:
            config: Конфигурация STT

        Raises:
            FileNotFoundError: Если модель Vosk не найдена
            RuntimeError: Если не удалось инициализировать модель
        """
        self.config = config

        # Проверка существования модели
        if not os.path.exists(config.model_path):
            error_msg = f"Модель Vosk не найдена по пути: {config.model_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Загрузка модели Vosk
        try:
            logger.info(f"Загрузка модели Vosk для STT из {config.model_path}...")
            self.model = vosk.Model(config.model_path)
            logger.info("Модель Vosk для STT загружена успешно")
        except Exception as e:
            error_msg = f"Ошибка загрузки модели Vosk для STT: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        # Инициализация распознавателя
        try:
            self.rec = vosk.KaldiRecognizer(self.model, config.sample_rate)
            self.rec.SetWords(True)  # Включаем получение слов
            logger.info("Распознаватель Vosk для STT инициализирован")
        except Exception as e:
            error_msg = f"Ошибка инициализации распознавателя STT: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        
        # Инициализация опционального VAD
        self.vad = OptionalVAD(
            enabled=config.use_vad,
            aggressiveness=config.vad_aggressiveness,
            sample_rate=config.sample_rate
        )

    def _convert_audio_to_bytes(self, data) -> bytes:
        """
        Безопасно преобразует аудиоданные в bytes.

        Args:
            data: Аудиоданные (numpy array, bytes, или другой формат)

        Returns:
            bytes: Аудиоданные в формате bytes

        Raises:
            ValueError: Если данные не могут быть преобразованы
        """
        if data is None:
            raise ValueError("Аудиоданные пусты (None)")

        try:
            # Если data уже bytes, используем как есть
            if isinstance(data, bytes):
                return data

            # Если data имеет метод tobytes (numpy array)
            if hasattr(data, 'tobytes'):
                return data.tobytes()

            # Пытаемся преобразовать через numpy
            import numpy as np
            if isinstance(data, (list, tuple)):
                data = np.array(data, dtype=np.int16)
            elif not isinstance(data, np.ndarray):
                data = np.array(data, dtype=np.int16)

            return data.tobytes()
        except Exception as e:
            raise ValueError(f"Не удалось преобразовать аудиоданные в bytes: {e}")

    def _is_silence(self, audio_chunk, threshold: float = 500.0) -> bool:
        """
        Проверяет, является ли аудио-чанк тишиной.

        Args:
            audio_chunk: Массив аудиоданных
            threshold: Порог амплитуды для определения тишины

        Returns:
            bool: True, если это тишина
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            return True

        try:
            # Вычисляем среднее абсолютное значение амплитуды
            # sounddevice возвращает numpy array, используем его методы
            import numpy as np
            if not isinstance(audio_chunk, np.ndarray):
                audio_chunk = np.array(audio_chunk, dtype=np.float32)
            amplitude = float(np.abs(audio_chunk).mean())
            return amplitude < threshold
        except Exception as e:
            logger.debug(f"Ошибка при проверке тишины: {e}, считаем тишиной")
            return True

    def _parse_result_with_confidence(
        self, result_json: dict
    ) -> tuple[str, float, list[dict]]:
        """
        Парсит результат распознавания и вычисляет среднюю уверенность по словам.

        Args:
            result_json: JSON-объект результата от Vosk

        Returns:
            tuple[str, float, list[dict]]: текст, средняя уверенность, список слов с conf
        """
        text = result_json.get("text", "").strip()
        words_with_conf = []

        # Пытаемся извлечь уверенность по словам из поля "result"
        if "result" in result_json and isinstance(result_json["result"], list):
            words_with_conf = [
                word
                for word in result_json["result"]
                if isinstance(word, dict) and "word" in word
            ]

        # Вычисляем среднюю уверенность
        avg_conf = 1.0  # По умолчанию полная уверенность
        if words_with_conf:
            confidences = [
                word.get("conf", 1.0) for word in words_with_conf if "conf" in word
            ]
            if confidences:
                avg_conf = sum(confidences) / len(confidences)

        return text, avg_conf, words_with_conf

    def listen_once(self) -> Optional[str]:
        """
        Блокирующе слушает микрофон одну фразу до тишины или таймаута.

        Returns:
            Optional[str]: Распознанный текст или None, если ничего не распознано
        """
        logger.info("STT: начинаю слушать фразу...")

        start_time = time.time()
        last_speech_time = None
        collected_text = ""
        collected_result_json = None
        speech_detected = False

        try:
            # Проверка доступности микрофона
            try:
                default_input = sd.default.device[0]
                if default_input is None:
                    logger.warning("Устройство ввода по умолчанию не найдено, используем системное")
            except Exception:
                logger.debug("Не удалось определить устройство ввода, продолжаем...")
            
            input_kwargs = {
                "samplerate": self.config.sample_rate,
                "blocksize": self.config.chunk_size,
                "dtype": "int16",
                "channels": 1,
                "latency": "low",
                "extra_settings": None,
            }
            # Добавляем device только если указан
            if self.config.device_index is not None:
                input_kwargs["device"] = self.config.device_index
            
            with sd.InputStream(**input_kwargs) as stream:
                if self.config.device_index is not None:
                    logger.debug(f"STT: микрофон открыт (device_index={self.config.device_index})")
                else:
                    logger.debug("STT: микрофон открыт (устройство по умолчанию)")

                # Сбрасываем распознаватель перед началом новой фразы
                self.rec = vosk.KaldiRecognizer(
                    self.model, self.config.sample_rate
                )
                self.rec.SetWords(True)

                while True:
                    current_time = time.time()
                    elapsed = current_time - start_time

                    # Проверка максимальной длительности
                    if elapsed >= self.config.max_phrase_duration:
                        logger.info(
                            f"Достигнут лимит времени ({self.config.max_phrase_duration}с)"
                        )
                        break

                    # Читаем аудиоданные с обработкой ошибки 247
                    try:
                        data, _ = stream.read(self.config.chunk_size)
                    except Exception as e:
                        error_code = getattr(e, 'errno', None)
                        error_msg = str(e)
                        
                        # Ошибка 247 - проблема с буферизацией/таймаутом
                        if error_code == 247 or '247' in error_msg:
                            logger.debug(f"Ошибка 247 при чтении аудио (буферизация), повторная попытка...")
                            import time
                            time.sleep(0.01)  # Небольшая задержка для стабилизации буфера
                            try:
                                # Пробуем прочитать с меньшим размером блока
                                read_size = max(self.config.chunk_size // 4, 1000)  # Минимум 1000 сэмплов
                                data, _ = stream.read(read_size)
                                if data is None or len(data) == 0:
                                    continue
                            except Exception as retry_e:
                                # Если и non-blocking не работает, просто пропускаем итерацию
                                logger.debug(f"Повторная попытка не удалась: {retry_e}, пропускаем итерацию")
                                continue
                        else:
                            logger.error(f"Ошибка чтения аудио (код: {error_code}): {error_msg}")
                            # Для критических ошибок прерываем цикл
                            if error_code and error_code not in [247, -9997]:  # -9997 тоже может быть временной ошибкой
                                break
                            continue

                    # Проверка данных перед обработкой
                    if data is None or len(data) == 0:
                        logger.debug("Получен пустой аудио-чанк, пропускаем")
                        continue

                    # Безопасное преобразование в bytes
                    try:
                        data_bytes = self._convert_audio_to_bytes(data)
                    except ValueError as e:
                        logger.error(f"Ошибка преобразования аудио данных: {e}")
                        continue

                    # Проверяем VAD (если включен) - пропускаем шум
                    if not self.vad.is_speech(data_bytes):
                        logger.debug("STT: VAD считает, что это тишина/шум, пропускаем чанк")
                        continue

                    # Проверяем, есть ли речь в чанке
                    is_silent = self._is_silence(data)

                    if not is_silent:
                        speech_detected = True
                        last_speech_time = current_time

                    # Передаём в распознаватель
                    if self.rec.AcceptWaveform(data_bytes):
                        # Финальный результат
                        result_str = self.rec.Result()
                        result = json.loads(result_str)
                        text = result.get("text", "").strip()

                        if text:
                            collected_text = text
                            collected_result_json = result
                            logger.debug(f"Распознано (final): '{text}'")

                    else:
                        # Частичный результат
                        partial_str = self.rec.PartialResult()
                        partial_result = json.loads(partial_str)
                        partial_text = partial_result.get("partial", "").strip()

                        if partial_text:
                            logger.debug(f"Распознано (partial): '{partial_text}'")

                    # Проверка тишины после речи
                    if (
                        speech_detected
                        and last_speech_time is not None
                        and is_silent
                    ):
                        silence_duration = current_time - last_speech_time

                        if silence_duration >= self.config.silence_timeout:
                            logger.info(
                                f"Обнаружена тишина {silence_duration:.2f}с, завершение фразы"
                            )
                            break

                # Получаем финальный результат, если он ещё не получен
                if not collected_text:
                    final_result_str = self.rec.FinalResult()
                    final_result = json.loads(final_result_str)
                    collected_text = final_result.get("text", "").strip()
                    if collected_text:
                        collected_result_json = final_result

        except KeyboardInterrupt:
            logger.info("Прослушивание прервано пользователем")
            return None
        except Exception as e:
            logger.error(f"Ошибка при прослушивании: {e}")
            return None

        # Обработка результата с фильтрацией по качеству
        duration = time.time() - start_time

        if not collected_text or not collected_text.strip():
            logger.warning("STT: речь не распознана или пустая")
            return None

        # Парсим результат с уверенностью
        if collected_result_json:
            text, avg_conf, words_with_conf = self._parse_result_with_confidence(
                collected_result_json
            )
        else:
            # Fallback: если JSON не сохранился, используем только текст
            text = collected_text.strip()
            avg_conf = 1.0
            words_with_conf = []

        # Логирование слов с уверенностью (если включено)
        if self.config.debug_log_words and words_with_conf:
            words_info = ", ".join(
                [
                    f"'{w.get('word', '')}'(conf={w.get('conf', 0.0):.2f})"
                    for w in words_with_conf
                ]
            )
            logger.debug(f"STT: слова с уверенностью: {words_info}")

        # Проверка минимальной длины фразы
        length = len(text.strip())
        if length < self.config.min_phrase_chars:
            logger.warning(
                f"STT: текст отклонён (слишком коротко) — "
                f"text='{text}', length={length}, "
                f"min_required={self.config.min_phrase_chars}"
            )
            return None

        # Проверка минимальной средней уверенности
        if avg_conf < self.config.min_avg_confidence:
            logger.warning(
                f"STT: текст отклонён (низкая уверенность) — "
                f"text='{text}', avg_conf={avg_conf:.2f}, "
                f"min_required={self.config.min_avg_confidence}"
            )
            return None

        # Фраза прошла все проверки
        logger.info(
            f"STT: финальный текст='{text}', "
            f"avg_conf={avg_conf:.2f}, "
            f"длительность={duration:.2f}с"
        )
        return text.strip()

    def listen_with_retries(self, max_retries: int = 2) -> Optional[str]:
        """
        Слушает микрофон с повторными попытками при неудачном распознавании.

        Args:
            max_retries: Максимальное количество повторных попыток

        Returns:
            Optional[str]: Распознанный текст или None, если все попытки неудачны
        """
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"Повторная попытка распознавания ({attempt}/{max_retries})...")

            text = self.listen_once()

            if text and text.strip():
                logger.info(f"Фраза успешно распознана с попытки {attempt + 1}")
                return text.strip()
            else:
                logger.warning(
                    f"STT: попытка №{attempt + 1} — "
                    f"ничего не распознано или низкое качество"
                )

        logger.warning(f"STT: все {max_retries + 1} попыток распознавания неудачны")
        return None

    def listen_once_with_confidence(self) -> Optional[Tuple[str, float]]:
        """
        Блокирующе слушает микрофон одну фразу и возвращает текст с уверенностью.
        
        Returns:
            Optional[Tuple[str, float]]: Кортеж (текст, средняя_уверенность) или None
        """
        logger.info("STT: начинаю слушать фразу (с возвратом уверенности)...")

        start_time = time.time()
        last_speech_time = None
        collected_text = ""
        collected_result_json = None
        speech_detected = False

        try:
            # Проверка доступности микрофона
            try:
                default_input = sd.default.device[0]
                if default_input is None:
                    logger.warning("Устройство ввода по умолчанию не найдено, используем системное")
            except Exception:
                logger.debug("Не удалось определить устройство ввода, продолжаем...")
            
            with sd.InputStream(
                samplerate=self.config.sample_rate,
                blocksize=self.config.chunk_size,
                dtype="int16",
                channels=1,
                latency='low',
                extra_settings=None,
            ) as stream:
                logger.debug("Микрофон открыт для STT (с уверенностью)")

                # Сбрасываем распознаватель перед началом новой фразы
                self.rec = vosk.KaldiRecognizer(
                    self.model, self.config.sample_rate
                )
                self.rec.SetWords(True)

                while True:
                    current_time = time.time()
                    elapsed = current_time - start_time

                    # Проверка максимальной длительности
                    if elapsed >= self.config.max_phrase_duration:
                        logger.info(
                            f"Достигнут лимит времени ({self.config.max_phrase_duration}с)"
                        )
                        break

                    # Читаем аудиоданные с обработкой ошибки 247
                    try:
                        data, _ = stream.read(self.config.chunk_size)
                    except Exception as e:
                        error_code = getattr(e, 'errno', None)
                        error_msg = str(e)
                        
                        if error_code == 247 or '247' in error_msg:
                            logger.debug(f"Ошибка 247 при чтении аудио (буферизация), повторная попытка...")
                            import time
                            time.sleep(0.01)
                            try:
                                read_size = max(self.config.chunk_size // 4, 1000)
                                data, _ = stream.read(read_size)
                                if data is None or len(data) == 0:
                                    continue
                            except Exception as retry_e:
                                logger.debug(f"Повторная попытка не удалась: {retry_e}, пропускаем итерацию")
                                continue
                        else:
                            logger.error(f"Ошибка чтения аудио (код: {error_code}): {error_msg}")
                            if error_code and error_code not in [247, -9997]:
                                break
                            continue

                    if data is None or len(data) == 0:
                        logger.debug("Получен пустой аудио-чанк, пропускаем")
                        continue

                    # Безопасное преобразование в bytes
                    try:
                        data_bytes = self._convert_audio_to_bytes(data)
                    except ValueError as e:
                        logger.error(f"Ошибка преобразования аудио данных: {e}")
                        continue

                    # Проверяем VAD (если включен)
                    if not self.vad.is_speech(data_bytes):
                        logger.debug("STT: VAD считает, что это тишина/шум, пропускаем чанк")
                        continue

                    # Проверяем, есть ли речь в чанке
                    is_silent = self._is_silence(data)

                    if not is_silent:
                        speech_detected = True
                        last_speech_time = current_time

                    # Передаём в распознаватель
                    if self.rec.AcceptWaveform(data_bytes):
                        result_str = self.rec.Result()
                        result = json.loads(result_str)
                        text = result.get("text", "").strip()

                        if text:
                            collected_text = text
                            collected_result_json = result
                            logger.debug(f"Распознано (final): '{text}'")

                    else:
                        partial_str = self.rec.PartialResult()
                        partial_result = json.loads(partial_str)
                        partial_text = partial_result.get("partial", "").strip()

                        if partial_text:
                            logger.debug(f"Распознано (partial): '{partial_text}'")

                    # Проверка тишины после речи
                    if (
                        speech_detected
                        and last_speech_time is not None
                        and is_silent
                    ):
                        silence_duration = current_time - last_speech_time

                        if silence_duration >= self.config.silence_timeout:
                            logger.info(
                                f"Обнаружена тишина {silence_duration:.2f}с, завершение фразы"
                            )
                            break

                # Получаем финальный результат, если он ещё не получен
                if not collected_text:
                    final_result_str = self.rec.FinalResult()
                    final_result = json.loads(final_result_str)
                    collected_text = final_result.get("text", "").strip()
                    if collected_text:
                        collected_result_json = final_result

        except KeyboardInterrupt:
            logger.info("Прослушивание прервано пользователем")
            return None
        except Exception as e:
            logger.error(f"Ошибка при прослушивании: {e}")
            return None

        # Обработка результата с фильтрацией по качеству
        duration = time.time() - start_time

        if not collected_text or not collected_text.strip():
            logger.warning("STT: речь не распознана или пустая")
            return None

        # Парсим результат с уверенностью
        if collected_result_json:
            text, avg_conf, words_with_conf = self._parse_result_with_confidence(
                collected_result_json
            )
        else:
            text = collected_text.strip()
            avg_conf = 1.0
            words_with_conf = []

        # Логирование слов с уверенностью (если включено)
        if self.config.debug_log_words and words_with_conf:
            words_info = ", ".join(
                [
                    f"'{w.get('word', '')}'(conf={w.get('conf', 0.0):.2f})"
                    for w in words_with_conf
                ]
            )
            logger.debug(f"STT: слова с уверенностью: {words_info}")

        # Проверка минимальной длины фразы
        length = len(text.strip())
        if length < self.config.min_phrase_chars:
            logger.warning(
                f"STT: текст отклонён (слишком коротко) — "
                f"text='{text}', length={length}, "
                f"min_required={self.config.min_phrase_chars}"
            )
            return None

        # Проверка минимальной средней уверенности
        if avg_conf < self.config.min_avg_confidence:
            logger.warning(
                f"STT: текст отклонён (низкая уверенность) — "
                f"text='{text}', avg_conf={avg_conf:.2f}, "
                f"min_required={self.config.min_avg_confidence}"
            )
            return None

        # Фраза прошла все проверки
        logger.info(
            f"STT: финальный текст='{text}', "
            f"avg_conf={avg_conf:.2f}, "
            f"длительность={duration:.2f}с"
        )
        return (text.strip(), avg_conf)

    def listen_once_for_confirmation(self, min_chars: int = 2) -> Optional[str]:
        """
        Слушает короткий ответ для подтверждения (например, "да"/"нет").
        Использует более мягкие критерии фильтрации для коротких слов.

        Args:
            min_chars: Минимальная длина ответа (по умолчанию 2 для "да"/"нет")

        Returns:
            Optional[str]: Распознанный текст или None
        """
        logger.info("STT: начинаю слушать подтверждение (короткий ответ)...")

        start_time = time.time()
        last_speech_time = None
        collected_text = ""
        collected_result_json = None
        speech_detected = False

        try:
            # Проверка доступности микрофона
            try:
                default_input = sd.default.device[0]
                if default_input is None:
                    logger.warning("Устройство ввода по умолчанию не найдено, используем системное")
            except Exception:
                logger.debug("Не удалось определить устройство ввода, продолжаем...")
            
            with sd.InputStream(
                samplerate=self.config.sample_rate,
                blocksize=self.config.chunk_size,
                dtype="int16",
                channels=1,
                latency='low',  # Низкая задержка для уменьшения проблем с буферизацией
                extra_settings=None,  # Используем настройки по умолчанию
            ) as stream:
                logger.debug("Микрофон открыт для STT (подтверждение)")

                # Сбрасываем распознаватель перед началом новой фразы
                self.rec = vosk.KaldiRecognizer(
                    self.model, self.config.sample_rate
                )
                self.rec.SetWords(True)

                while True:
                    current_time = time.time()
                    elapsed = current_time - start_time

                    # Для подтверждений используем меньший таймаут (5 секунд)
                    if elapsed >= 5.0:
                        logger.info("Достигнут лимит времени для подтверждения (5с)")
                        break

                    # Читаем аудиоданные с обработкой ошибки 247
                    try:
                        data, _ = stream.read(self.config.chunk_size)
                    except Exception as e:
                        error_code = getattr(e, 'errno', None)
                        error_msg = str(e)
                        
                        # Ошибка 247 - проблема с буферизацией/таймаутом
                        if error_code == 247 or '247' in error_msg:
                            logger.debug(f"Ошибка 247 при чтении аудио (буферизация), повторная попытка...")
                            import time
                            time.sleep(0.01)  # Небольшая задержка для стабилизации буфера
                            try:
                                # Пробуем прочитать с меньшим размером блока
                                read_size = max(self.config.chunk_size // 4, 1000)  # Минимум 1000 сэмплов
                                data, _ = stream.read(read_size)
                                if data is None or len(data) == 0:
                                    continue
                            except Exception as retry_e:
                                # Если и non-blocking не работает, просто пропускаем итерацию
                                logger.debug(f"Повторная попытка не удалась: {retry_e}, пропускаем итерацию")
                                continue
                        else:
                            logger.error(f"Ошибка чтения аудио (код: {error_code}): {error_msg}")
                            # Для критических ошибок прерываем цикл
                            if error_code and error_code not in [247, -9997]:  # -9997 тоже может быть временной ошибкой
                                break
                            continue

                    # Проверка данных перед обработкой
                    if data is None or len(data) == 0:
                        logger.debug("Получен пустой аудио-чанк, пропускаем")
                        continue

                    # Безопасное преобразование в bytes
                    try:
                        data_bytes = self._convert_audio_to_bytes(data)
                    except ValueError as e:
                        logger.error(f"Ошибка преобразования аудио данных: {e}")
                        continue

                    # Проверяем, есть ли речь в чанке
                    is_silent = self._is_silence(data)

                    if not is_silent:
                        speech_detected = True
                        last_speech_time = current_time

                    # Передаём в распознаватель
                    if self.rec.AcceptWaveform(data_bytes):
                        # Финальный результат
                        result_str = self.rec.Result()
                        result = json.loads(result_str)
                        text = result.get("text", "").strip()

                        if text:
                            collected_text = text
                            collected_result_json = result
                            logger.debug(f"Распознано (final): '{text}'")

                    # Проверка тишины после речи (более короткий таймаут для подтверждений)
                    if (
                        speech_detected
                        and last_speech_time is not None
                        and is_silent
                    ):
                        silence_duration = current_time - last_speech_time

                        if silence_duration >= 1.0:  # 1 секунда тишины для подтверждений
                            logger.info(
                                f"Обнаружена тишина {silence_duration:.2f}с, завершение подтверждения"
                            )
                            break

                # Получаем финальный результат, если он ещё не получен
                if not collected_text:
                    final_result_str = self.rec.FinalResult()
                    final_result = json.loads(final_result_str)
                    collected_text = final_result.get("text", "").strip()
                    if collected_text:
                        collected_result_json = final_result

        except KeyboardInterrupt:
            logger.info("Прослушивание прервано пользователем")
            return None
        except Exception as e:
            logger.error(f"Ошибка при прослушивании: {e}")
            return None

        # Обработка результата с более мягкими критериями для подтверждений
        duration = time.time() - start_time

        if not collected_text or not collected_text.strip():
            logger.warning("STT: подтверждение не распознано или пустое")
            return None

        # Парсим результат с уверенностью
        if collected_result_json:
            text, avg_conf, words_with_conf = self._parse_result_with_confidence(
                collected_result_json
            )
        else:
            text = collected_text.strip()
            avg_conf = 1.0
            words_with_conf = []

        # Для подтверждений используем более мягкие критерии:
        # - минимальная длина: min_chars (по умолчанию 2)
        # - минимальная уверенность: немного ниже, чем для обычных фраз (0.5)
        length = len(text.strip())
        if length < min_chars:
            logger.warning(
                f"STT: подтверждение отклонено (слишком коротко) — "
                f"text='{text}', length={length}, min_required={min_chars}"
            )
            return None

        # Более мягкая проверка уверенности для коротких подтверждений
        min_conf = 0.5  # Ниже, чем для обычных фраз
        if avg_conf < min_conf:
            logger.warning(
                f"STT: подтверждение отклонено (низкая уверенность) — "
                f"text='{text}', avg_conf={avg_conf:.2f}, min_required={min_conf}"
            )
            return None

        logger.info(
            f"STT: подтверждение распознано='{text}', "
            f"avg_conf={avg_conf:.2f}, длительность={duration:.2f}с"
        )
        return text.strip()

