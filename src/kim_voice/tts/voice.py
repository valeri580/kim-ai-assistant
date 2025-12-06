"""Модуль синтеза речи (TTS) для Windows - использует Windows COM для надёжной работы."""

import threading
from typing import Optional

from kim_core.logging import logger

# Пробуем использовать COM напрямую (предпочтительно для Windows)
try:
    import win32com.client
    COM_AVAILABLE = True
except ImportError:
    COM_AVAILABLE = False
    win32com = None

# Резервный вариант: pyttsx3
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    pyttsx3 = None


class KimVoice:
    """
    Класс для синтеза речи.
    
    Использует Windows COM (SAPI) напрямую для гарантированной работы с аудиоустройствами.
    Если COM недоступен, использует pyttsx3 как резервный вариант.
    """

    def __init__(self, rate: int = 0, volume: int = 100) -> None:
        """
        Инициализирует движок синтеза речи.

        Args:
            rate: Скорость речи (-10 до 10, где 0 - нормальная для COM) или слов/минуту (для pyttsx3)
            volume: Громкость (0-100 для COM) или (0.0-1.0 для pyttsx3)
        """
        self.speaker: Optional[object] = None  # COM speaker
        self.engine: Optional[object] = None  # pyttsx3 engine (резерв)
        self._lock = threading.Lock()
        self.use_com = False

        # Пробуем использовать COM напрямую (предпочтительно)
        if COM_AVAILABLE:
            try:
                self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
                logger.info("TTS движок (Windows COM) инициализирован")
                self.use_com = True

                # Настраиваем аудиоустройство
                self._setup_audio_device_com()

                # Настраиваем голос
                self._setup_voice_com()

                # Конвертируем параметры для COM
                com_rate = self._convert_rate_to_com(rate)
                com_volume = self._convert_volume_to_com(volume)
                
                self.speaker.Volume = com_volume
                self.speaker.Rate = com_rate

                logger.info(f"TTS настроен (COM): скорость={self.speaker.Rate}, громкость={self.speaker.Volume}%")
                return

            except Exception as e:
                logger.warning(f"Ошибка инициализации COM: {e}, пробую pyttsx3")
                self.speaker = None
                self.use_com = False

        # Резервный вариант: pyttsx3
        if PYTTSX3_AVAILABLE and not self.use_com:
            try:
                try:
                    self.engine = pyttsx3.init(driverName='sapi5')
                except Exception:
                    self.engine = pyttsx3.init()
                logger.info("TTS движок (pyttsx3) инициализирован")

                # Выбираем женский/русский голос
                voices = self.engine.getProperty("voices")
                if voices:
                    for voice in voices:
                        voice_id = str(voice.id).lower()
                        voice_name = str(voice.name).lower()
                        if any(keyword in voice_id or keyword in voice_name 
                               for keyword in ["female", "woman", "женский", "жен", "irina"]):
                            self.engine.setProperty("voice", voice.id)
                            logger.info(f"Выбран голос: {voice.name}")
                            break

                # Конвертируем параметры для pyttsx3
                pyttsx3_rate = rate if isinstance(rate, int) and rate > 50 else 170
                pyttsx3_volume = volume if isinstance(volume, float) and volume <= 1.0 else (volume / 100.0 if volume > 1 else 1.0)
                
                self.engine.setProperty("rate", pyttsx3_rate)
                self.engine.setProperty("volume", pyttsx3_volume)

                logger.info(f"TTS настроен (pyttsx3): скорость={pyttsx3_rate}, громкость={pyttsx3_volume}")

            except Exception as e:
                logger.error(f"Ошибка инициализации pyttsx3: {e}")
                self.engine = None

        if not self.speaker and not self.engine:
            logger.error("Не удалось инициализировать ни COM, ни pyttsx3")

    def _convert_rate_to_com(self, rate: int) -> int:
        """Конвертирует скорость в формат COM (-10 до 10)."""
        if -10 <= rate <= 10:
            return rate
        # Если передано в словах/минуту (например, 170), конвертируем
        if rate > 50:
            # 170 слов/мин ≈ 0, диапазон примерно -10 до 10
            return max(-10, min(10, int((rate - 170) / 17)))
        return 0

    def _convert_volume_to_com(self, volume: int | float) -> int:
        """Конвертирует громкость в формат COM (0-100)."""
        if isinstance(volume, float) and volume <= 1.0:
            return min(100, max(0, int(volume * 100)))
        return min(100, max(0, int(volume)))

    def _setup_audio_device_com(self) -> None:
        """Настраивает аудиоустройство для COM."""
        try:
            audio_outputs = self.speaker.GetAudioOutputs()
            
            # Ищем предпочтительное устройство
            target_device = None
            keywords = ["BLUETOOTH", "HEADPHONES", "SBERBOOM", "1205"]
            
            # Логируем все доступные устройства
            logger.debug(f"Доступных аудиоустройств: {audio_outputs.Count}")
            for i in range(audio_outputs.Count):
                output = audio_outputs.Item(i)
                desc = output.GetDescription()
                logger.debug(f"  - {desc}")
            
            for i in range(audio_outputs.Count):
                output = audio_outputs.Item(i)
                desc = output.GetDescription()
                
                if any(keyword in desc.upper() for keyword in keywords):
                    target_device = output
                    logger.info(f"Найдено предпочтительное аудиоустройство: {desc}")
                    break
            
            if target_device:
                try:
                    # Устанавливаем устройство
                    self.speaker.AudioOutput = target_device
                    
                    # Проверяем, что устройство установлено (если метод доступен)
                    try:
                        current_output = self.speaker.GetAudioOutputId()
                        logger.debug(f"Текущее устройство ID: {current_output}")
                    except:
                        pass  # Метод может быть недоступен
                    
                    logger.info(f"Аудиоустройство установлено: {target_device.GetDescription()}")
                    logger.info("ВНИМАНИЕ: Если звука нет, убедитесь, что это устройство выбрано как устройство по умолчанию в Windows")
                    logger.info("  (Параметры → Система → Звук → Выбор устройства вывода)")
                    
                except Exception as e:
                    logger.warning(f"Не удалось установить устройство программно: {e}")
                    logger.info("SAPI будет использовать устройство по умолчанию Windows")
                    logger.info("Убедитесь, что Bluetooth колонка выбрана как устройство по умолчанию")
            else:
                logger.debug("Предпочтительное устройство не найдено, используется устройство по умолчанию")
                logger.info("Убедитесь, что Bluetooth колонка выбрана как устройство по умолчанию в Windows")
                
        except Exception as e:
            logger.debug(f"Ошибка настройки аудиоустройства: {e}")

    def _setup_voice_com(self) -> None:
        """Настраивает голос для COM."""
        try:
            voices = self.speaker.GetVoices()
            
            # Список приоритетов: сначала ищем более качественные голоса
            preferred_keywords = [
                "NEURAL",  # Neural голоса более естественные
                "PREMIUM",  # Premium голоса
                "IRINA",    # Стандартный русский голос
                "RU-RU",    # Русский голос по локали
            ]
            
            selected_voice = None
            selected_priority = 999
            
            # Проходим по всем голосам и находим лучший
            for i in range(voices.Count):
                voice = voices.Item(i)
                voice_id = str(voice.Id).upper()
                voice_desc = str(voice.GetDescription()).upper()
                
                # Проверяем, является ли это русским голосом
                is_russian = ("IRINA" in voice_id or "RU-RU" in voice_id or 
                             "RUSSIAN" in voice_desc or "RU" in voice_id)
                
                if is_russian:
                    # Определяем приоритет (чем меньше число, тем выше приоритет)
                    priority = 999
                    for idx, keyword in enumerate(preferred_keywords):
                        if keyword in voice_id or keyword in voice_desc:
                            priority = idx
                            break
                    
                    # Выбираем голос с наивысшим приоритетом
                    if priority < selected_priority:
                        selected_voice = voice
                        selected_priority = priority
            
            if selected_voice:
                self.speaker.Voice = selected_voice
                logger.info(f"Выбран голос: {selected_voice.GetDescription()}")
                return
                    
            logger.debug("Русский голос не найден, используется голос по умолчанию")
        except Exception as e:
            logger.debug(f"Ошибка настройки голоса: {e}")

    def set_rate(self, rate: int) -> None:
        """
        Обновляет скорость речи.

        Args:
            rate: Скорость речи (-10 до 10 для COM) или слов/минуту (для pyttsx3)
        """
        with self._lock:
            if self.use_com and self.speaker:
                com_rate = self._convert_rate_to_com(rate)
                self.speaker.Rate = com_rate
                logger.debug(f"TTS скорость обновлена (COM): {self.speaker.Rate}")
            elif self.engine:
                pyttsx3_rate = rate if isinstance(rate, int) and rate > 50 else 170
                self.engine.setProperty("rate", pyttsx3_rate)
                logger.debug(f"TTS скорость обновлена (pyttsx3): {pyttsx3_rate}")

    def set_volume(self, volume: int) -> None:
        """
        Обновляет громкость.

        Args:
            volume: Громкость (0-100 для COM) или (0.0-1.0 для pyttsx3)
        """
        with self._lock:
            if self.use_com and self.speaker:
                com_volume = self._convert_volume_to_com(volume)
                self.speaker.Volume = com_volume
                logger.debug(f"TTS громкость обновлена (COM): {self.speaker.Volume}%")
            elif self.engine:
                pyttsx3_volume = volume if isinstance(volume, float) and volume <= 1.0 else (volume / 100.0 if volume > 1 else 1.0)
                self.engine.setProperty("volume", pyttsx3_volume)
                logger.debug(f"TTS громкость обновлена (pyttsx3): {pyttsx3_volume}")

    def speak(self, text: str) -> None:
        """
        Озвучивает текст.

        Args:
            text: Текст для озвучки
        """
        if not text or not text.strip():
            logger.warning("Пустой текст для озвучки")
            return

        if not self.speaker and not self.engine:
            logger.error("TTS движок не инициализирован, невозможно озвучить текст")
            return

        try:
            logger.info(f"Озвучивание: {text}")

            # Используем COM (предпочтительно) - работает гарантированно с Bluetooth
            if self.use_com and self.speaker:
                # Убеждаемся, что громкость максимальная
                if self.speaker.Volume < 100:
                    self.speaker.Volume = 100
                    logger.debug(f"Громкость установлена на максимум: {self.speaker.Volume}%")
                
                with self._lock:
                    # Обычный синхронный режим (более надёжный)
                    self.speaker.Speak(text)
                
                logger.debug("Озвучка завершена (COM)")
                return

            # Резервный вариант: pyttsx3
            if self.engine:
                current_volume = self.engine.getProperty("volume")
                if current_volume < 0.5:
                    logger.warning(f"Громкость низкая ({current_volume}), увеличиваю до 1.0")
                    self.engine.setProperty("volume", 1.0)
                
                with self._lock:
                    try:
                        self.engine.stop()
                    except Exception:
                        pass
                    
                    self.engine.say(text)
                    self.engine.runAndWait()

                logger.debug("Озвучка завершена (pyttsx3)")

        except Exception as e:
            logger.error(f"Ошибка при озвучке: {e}")

    def __del__(self) -> None:
        """Очистка ресурсов при удалении объекта."""
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
