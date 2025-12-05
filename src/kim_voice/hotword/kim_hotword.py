"""Модуль детекции ключевого слова «Ким» через Vosk."""

import json
import os
import string
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import sounddevice as sd
import vosk

from kim_core.logging import logger


@dataclass
class HotwordConfig:
    """Конфигурация детекции hotword."""

    model_path: str  # путь к модели Vosk
    sample_rate: int = 16000
    chunk_size: int = 4000
    confidence_threshold: float = 0.7
    debounce_seconds: float = 1.2
    min_hotword_confidence: float = 0.5  # нижний порог средней уверенности по словам
    require_strict_word_match: bool = True  # если True — искать отдельное слово "ким"
    min_chars_in_utterance: int = 2  # минимальная длина всей фразы
    adaptive_threshold: bool = True  # использовать адаптивный порог на основе шума
    noise_floor_window: int = 100  # количество чанков для оценки шума
    min_confidence_floor: float = 0.5  # нижняя граница порога
    max_confidence_floor: float = 0.9  # верхняя граница порога
    device_index: Optional[int] = None  # индекс устройства ввода (микрофон), None = по умолчанию


class KimHotwordListener:
    """Слушатель ключевого слова «Ким» через Vosk."""

    def __init__(self, config: HotwordConfig) -> None:
        """
        Инициализирует слушатель hotword.

        Args:
            config: Конфигурация детекции

        Raises:
            FileNotFoundError: Если модель Vosk не найдена
            RuntimeError: Если не удалось инициализировать модель
        """
        self.config = config
        self.last_trigger_ts: float = 0.0
        
        # Буферы для адаптивного порога на основе шума
        self._noise_amplitudes: list[float] = []
        self._dynamic_conf_threshold: float = config.min_hotword_confidence

        # Проверка существования модели
        if not os.path.exists(config.model_path):
            error_msg = f"Модель Vosk не найдена по пути: {config.model_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Загрузка модели Vosk
        try:
            logger.info(f"Загрузка модели Vosk из {config.model_path}...")
            self.model = vosk.Model(config.model_path)
            logger.info("Модель Vosk загружена успешно")
        except Exception as e:
            error_msg = f"Ошибка загрузки модели Vosk: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        # Инициализация распознавателя
        try:
            self.rec = vosk.KaldiRecognizer(self.model, config.sample_rate)
            self.rec.SetWords(True)  # Включаем получение слов для confidence
            logger.info("Распознаватель Vosk инициализирован")
        except Exception as e:
            error_msg = f"Ошибка инициализации распознавателя: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _is_hotword(self, text: str) -> bool:
        """
        Проверяет, является ли текст ключевым словом.

        Args:
            text: Распознанный текст

        Returns:
            bool: True, если обнаружено ключевое слово
        """
        if not text:
            return False

        # Нормализуем текст: lower, удаляем знаки препинания
        normalized = text.lower().strip()
        # Заменяем знаки препинания пробелами
        for punct in string.punctuation:
            normalized = normalized.replace(punct, " ")
        # Разбиваем по пробелам и убираем пустые
        words = [w for w in normalized.split() if w]

        if not words:
            return False

        # Если требуется строгое совпадение слова
        if self.config.require_strict_word_match:
            # Проверяем, что одно из слов точно равно "ким"
            result = any(word == "ким" for word in words)
            if not result:
                logger.debug(
                    f"Hotword: строгое совпадение не найдено. "
                    f"Слова: {words}, ищем 'ким'"
                )
            return result
        else:
            # Fallback: проверяем наличие подстроки "ким" в словах
            result = any("ким" in word for word in words) or normalized == "ким"
            if not result:
                logger.debug(
                    f"Hotword: подстрока 'ким' не найдена. "
                    f"Слова: {words}, нормализованный текст: '{normalized}'"
                )
            return result

    def _parse_result(self, result_str: str) -> tuple[Optional[str], float]:
        """
        Парсит результат распознавания Vosk.

        Args:
            result_str: JSON-строка результата

        Returns:
            tuple[Optional[str], float]: Текст и уровень уверенности
        """
        try:
            result = json.loads(result_str)
            text = result.get("text", "").strip()
            confidence = 1.0  # По умолчанию полная уверенность

            # Пытаемся извлечь confidence из результата
            if "confidence" in result:
                confidence = float(result["confidence"])
            elif "result" in result and isinstance(result["result"], list):
                # Если есть список результатов, берём средний confidence
                confidences = [
                    r.get("conf", 1.0)
                    for r in result["result"]
                    if isinstance(r, dict) and "conf" in r
                ]
                if confidences:
                    confidence = sum(confidences) / len(confidences)

            return text if text else None, confidence

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Ошибка парсинга результата: {e}")
            return None, 0.0

    def listen(self, on_trigger: Callable[[], None]) -> None:
        """
        Начинает прослушивание микрофона и вызывает callback при обнаружении hotword.

        Args:
            on_trigger: Функция-колбэк, вызываемая при обнаружении ключевого слова
        """
        logger.info("Hotword: start listening loop")
        logger.info(
            "Hotword config: "
            f"sample_rate={self.config.sample_rate}, "
            f"chunk_size={self.config.chunk_size}, "
            f"confidence_threshold={self.config.confidence_threshold}, "
            f"min_hotword_confidence={self.config.min_hotword_confidence}, "
            f"min_chars_in_utterance={self.config.min_chars_in_utterance}, "
            f"debounce_seconds={self.config.debounce_seconds}, "
            f"require_strict_word_match={self.config.require_strict_word_match}"
        )

        try:
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
                logger.info(f"Hotword: использует микрофон с индексом {self.config.device_index}")
            
            with sd.InputStream(**input_kwargs) as stream:
                logger.info("Микрофон открыт, ожидание ключевого слова «Ким»...")
                logger.info("Начинаю обработку аудиопотока...")

                chunk_count = 0
                while True:
                    chunk_count += 1
                    # Логируем каждые 50 чанков для видимости процесса
                    if chunk_count % 50 == 0:
                        logger.info(f"Обработано {chunk_count} аудио-чанков (микрофон работает)...")
                    try:
                        # Читаем аудиоданные с обработкой ошибки 247
                        try:
                            data, overflowed = stream.read(self.config.chunk_size)
                            if overflowed:
                                logger.warning("Переполнение буфера аудио!")
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
                                logger.debug(f"Ошибка чтения аудио (код: {error_code}): {error_msg}")
                                # Для критических ошибок логируем, но продолжаем
                                if error_code and error_code not in [247, -9997]:
                                    logger.warning(f"Критическая ошибка аудио: {error_code}")
                                continue
                        
                        # Проверка данных перед обработкой
                        if data is None or len(data) == 0:
                            logger.debug("Hotword: получен пустой аудио-чанк, пропускаем")
                            continue

                        # Диагностика уровня сигнала и сбор данных для адаптивного порога
                        try:
                            import numpy as np

                            if isinstance(data, np.ndarray):
                                amplitude = float(np.abs(data).mean())
                                
                                # Собираем амплитуды для оценки шума (адаптивный порог)
                                if self.config.adaptive_threshold:
                                    self._noise_amplitudes.append(amplitude)
                                    # Ограничиваем размер буфера
                                    if len(self._noise_amplitudes) > self.config.noise_floor_window:
                                        self._noise_amplitudes.pop(0)  # Удаляем старейшее значение
                                
                                if chunk_count % 200 == 0:
                                    logger.debug(
                                        f"Hotword: амплитуда аудио-чунка={amplitude:.2f}"
                                    )
                                    
                                    # Периодически обновляем адаптивный порог
                                    if self.config.adaptive_threshold and len(self._noise_amplitudes) >= 50:
                                        noise_level = sum(self._noise_amplitudes) / len(self._noise_amplitudes)
                                        # Подстраиваем порог: при низком шуме - выше порог, при высоком - ниже
                                        # Нормализуем noise_level (примерно от 0 до 10000 для типичных значений)
                                        # Чем выше шум, тем ниже порог (но в пределах min/max)
                                        noise_normalized = min(noise_level / 1000.0, 1.0)  # Примерная нормализация
                                        self._dynamic_conf_threshold = (
                                            self.config.max_confidence_floor * (1.0 - noise_normalized * 0.4) +
                                            self.config.min_confidence_floor * (noise_normalized * 0.4)
                                        )
                                        # Ограничиваем в пределах min/max
                                        self._dynamic_conf_threshold = max(
                                            self.config.min_confidence_floor,
                                            min(self.config.max_confidence_floor, self._dynamic_conf_threshold)
                                        )
                                        logger.info(
                                            f"Hotword: адаптивный порог обновлён, "
                                            f"noise_level={noise_level:.2f}, "
                                            f"dynamic_conf_threshold={self._dynamic_conf_threshold:.2f}"
                                        )
                                
                                if amplitude == 0.0:
                                    logger.debug(
                                        "Hotword: аудио-чанк состоит из нулей (тишина)"
                                    )
                        except Exception:
                            # Диагностика амплитуды не критична
                            pass
                        
                        # Безопасное преобразование в bytes
                        try:
                            if hasattr(data, 'tobytes'):
                                data_bytes = data.tobytes()
                            elif isinstance(data, bytes):
                                data_bytes = data
                            else:
                                import numpy as np
                                data_bytes = np.array(data, dtype=np.int16).tobytes()
                        except Exception as e:
                            logger.debug(f"Ошибка преобразования аудио данных: {e}")
                            continue

                        # Диагностика размера буфера в байтах
                        if chunk_count % 100 == 0:
                            logger.debug(
                                f"Hotword: got audio chunk, len(bytes)={len(data_bytes)}"
                            )

                        # Передаём в распознаватель
                        try:
                            result_ready = self.rec.AcceptWaveform(data_bytes)
                            # Логируем каждые 500 вызовов для диагностики
                            if chunk_count % 500 == 0:
                                logger.info(
                                    f"Hotword: AcceptWaveform вызван {chunk_count} раз, "
                                    f"result_ready={result_ready}"
                                )
                            else:
                                logger.debug(f"Hotword: AcceptWaveform -> {result_ready}")
                        except Exception as e:
                            logger.warning(f"Ошибка AcceptWaveform: {e}")
                            continue
                        
                        if result_ready:
                            # Финальный результат
                            try:
                                result_str = self.rec.Result()
                                logger.debug(
                                    f"Hotword: final result JSON = {result_str}"
                                )
                                text, avg_conf = self._parse_result(result_str)
                            except Exception as e:
                                logger.warning(f"Ошибка получения результата: {e}")
                                continue

                            if text:
                                length = len(text.strip())

                                # Логирование каждого финального результата (INFO для видимости)
                                logger.info(
                                    "Hotword: распознано "
                                    f"text='{text}', length={length}, "
                                    f"avg_conf={avg_conf:.2f}"
                                )

                                # Фильтр 1: минимальная длина фразы
                                if length < self.config.min_chars_in_utterance:
                                    logger.info(
                                        f"Hotword: фраза слишком короткая (length={length}, "
                                        f"min={self.config.min_chars_in_utterance}), игнорируем"
                                    )
                                    continue

                                # Фильтр 2: минимальная средняя уверенность (адаптивный или статический)
                                # Определяем порог для проверки
                                confidence_threshold = (
                                    self._dynamic_conf_threshold
                                    if self.config.adaptive_threshold
                                    else self.config.min_hotword_confidence
                                )
                                
                                if avg_conf < confidence_threshold:
                                    logger.info(
                                        f"Hotword: низкая уверенность (avg_conf={avg_conf:.2f}, "
                                        f"threshold={confidence_threshold:.2f}, "
                                        f"adaptive={self.config.adaptive_threshold}), игнорируем"
                                    )
                                    continue
                                
                                # Логируем, какой порог использовался
                                if self.config.adaptive_threshold:
                                    logger.debug(
                                        f"Hotword: проверка уверенности пройдена "
                                        f"(avg_conf={avg_conf:.2f} >= threshold={confidence_threshold:.2f}, adaptive)"
                                    )

                                # Проверяем, является ли это hotword
                                is_hotword = self._is_hotword(text)
                                logger.info(
                                    "Hotword: проверка слова -> "
                                    f"text='{text}', length={length}, "
                                    f"avg_conf={avg_conf:.2f}, "
                                    f"is_hotword={is_hotword}, "
                                    f"require_strict={self.config.require_strict_word_match}"
                                )

                                if is_hotword:
                                    # Проверяем debounce
                                    current_time = time.time()
                                    time_since_last = (
                                        current_time - self.last_trigger_ts
                                    )

                                    if time_since_last >= self.config.debounce_seconds:
                                        logger.info(
                                            "Hotword: TRIGGER fired "
                                            f"text='{text}', avg_conf={avg_conf:.2f}, "
                                            f"now={current_time:.3f}, "
                                            f"last_trigger_ts={self.last_trigger_ts:.3f}, "
                                            f"time_since_last={time_since_last:.3f}"
                                        )
                                        self.last_trigger_ts = current_time
                                        on_trigger()
                                    else:
                                        logger.debug(
                                            f"Hotword: игнорировано (debounce) — "
                                            f"{time_since_last:.2f}с с последнего срабатывания"
                                        )
                                else:
                                    # Если это не hotword, логируем для отладки
                                    logger.debug(
                                        f"Hotword: '{text}' не является ключевым словом 'Ким'"
                                    )
                        else:
                            # Частичный результат - логируем для диагностики (INFO для видимости)
                            try:
                                partial_str = self.rec.PartialResult()
                                if partial_str:
                                    partial_result = json.loads(partial_str)
                                    partial_text = partial_result.get("partial", "").strip()
                                    if partial_text:
                                        logger.info(f"Hotword: partial='{partial_text}'")
                            except Exception:
                                pass  # Игнорируем ошибки парсинга частичных результатов

                    except KeyboardInterrupt:
                        logger.info("Получен сигнал остановки (KeyboardInterrupt)")
                        break
                    except Exception as e:
                        logger.error(f"Ошибка при обработке аудио: {e}")
                        import traceback
                        logger.debug(f"Трассировка: {traceback.format_exc()}")
                        # Продолжаем работу после ошибки, но делаем небольшую паузу
                        import time
                        time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Прослушивание прервано пользователем")
        except Exception as e:
            logger.error(f"Критическая ошибка при прослушивании: {e}")
            raise
        finally:
            logger.info("Прослушивание микрофона остановлено")

