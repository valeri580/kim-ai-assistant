"""Модуль синтеза речи (TTS) через Windows COM (SAPI) - надёжная реализация."""

import threading
from typing import Optional

from kim_core.logging import logger

try:
    import win32com.client
    COM_AVAILABLE = True
except ImportError:
    COM_AVAILABLE = False
    win32com = None


class KimVoiceCOM:
    """Класс для синтеза речи через Windows COM (SAPI) - работает напрямую с аудиоустройствами."""

    def __init__(self, rate: int = 0, volume: int = 100) -> None:
        """
        Инициализирует движок синтеза речи через Windows COM.

        Args:
            rate: Скорость речи (-10 до 10, где 0 - нормальная)
            volume: Громкость (0-100)
        """
        self.speaker: Optional[object] = None
        self._lock = threading.Lock()
        self.rate = rate
        self.volume = volume

        if not COM_AVAILABLE:
            logger.error("win32com не доступен. Установите: pip install pywin32")
            return

        try:
            self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
            logger.info("TTS движок (Windows COM) инициализирован")

            # Настраиваем аудиоустройство
            self._setup_audio_device()

            # Настраиваем голос
            self._setup_voice()

            # Устанавливаем параметры
            self.speaker.Volume = min(max(volume, 0), 100)  # Ограничиваем 0-100
            self.speaker.Rate = min(max(rate, -10), 10)  # Ограничиваем -10 до 10

            logger.info(f"TTS настроен: скорость={self.speaker.Rate}, громкость={self.speaker.Volume}%")

        except Exception as e:
            logger.error(f"Ошибка инициализации TTS (COM): {e}")
            self.speaker = None

    def _setup_audio_device(self) -> None:
        """Настраивает аудиоустройство для SAPI."""
        try:
            audio_outputs = self.speaker.GetAudioOutputs()
            
            # Ищем предпочтительное устройство (Bluetooth, Headphones, SberBoom)
            target_device = None
            keywords = ["BLUETOOTH", "HEADPHONES", "SBERBOOM", "1205"]
            
            for i in range(audio_outputs.Count):
                output = audio_outputs.Item(i)
                desc = output.GetDescription()
                
                if any(keyword in desc.upper() for keyword in keywords):
                    target_device = output
                    logger.info(f"Найдено предпочтительное аудиоустройство: {desc}")
                    break
            
            if target_device:
                # Устанавливаем устройство
                try:
                    self.speaker.AudioOutput = target_device
                    logger.info(f"Аудиоустройство установлено: {target_device.GetDescription()}")
                except Exception as e:
                    logger.warning(f"Не удалось установить аудиоустройство: {e}")
                    logger.info("Используется устройство по умолчанию Windows")
            else:
                logger.info("Предпочтительное устройство не найдено, используется устройство по умолчанию")
                
        except Exception as e:
            logger.debug(f"Ошибка настройки аудиоустройства: {e}")

    def _setup_voice(self) -> None:
        """Настраивает голос для синтеза."""
        try:
            voices = self.speaker.GetVoices()
            russian_voice = None

            # Ищем русский голос (Irina)
            for i in range(voices.Count):
                voice = voices.Item(i)
                voice_id = str(voice.Id).upper()
                voice_desc = voice.GetDescription().upper()

                if "IRINA" in voice_id or "RU-RU" in voice_id or "RUSSIAN" in voice_desc:
                    russian_voice = voice
                    break

            if russian_voice:
                self.speaker.Voice = russian_voice
                logger.info(f"Выбран голос: {russian_voice.GetDescription()}")
            else:
                logger.warning("Русский голос не найден, используется голос по умолчанию")
                
        except Exception as e:
            logger.warning(f"Ошибка настройки голоса: {e}")

    def speak(self, text: str) -> None:
        """
        Озвучивает текст.

        Args:
            text: Текст для озвучки
        """
        if not self.speaker:
            logger.error("TTS движок не инициализирован, невозможно озвучить текст")
            return

        if not text or not text.strip():
            logger.warning("Пустой текст для озвучки")
            return

        try:
            logger.info(f"Озвучивание: {text}")

            # Убеждаемся, что громкость максимальная
            if self.speaker.Volume < 100:
                self.speaker.Volume = 100
                logger.debug(f"Громкость установлена на максимум: {self.speaker.Volume}%")

            with self._lock:
                self.speaker.Speak(text)

            logger.debug("Озвучка завершена")

        except Exception as e:
            logger.error(f"Ошибка при озвучке: {e}")

