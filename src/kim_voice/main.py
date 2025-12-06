"""Точка входа голосового ассистента (локально, Windows)."""

import asyncio
import os
import sys

from dotenv import load_dotenv

from typing import Optional

from kim_core.config import load_config
from kim_core.config.runtime import (
    RuntimeSettings,
    RuntimeSettingsStore,
    merge_config_with_runtime,
)
from kim_core.config.settings import AppConfig
from kim_core.llm import BudgetExceededError, LLMError, LLMRouter, OpenRouterClient
from kim_core.logging import init_logger, logger
from kim_core.prompts import get_system_prompt
from kim_desktop.files.file_manager import (
    AliasNotFoundError,
    FileManagerError,
    PathTraversalError,
    find_latest_file,
    move_file,
    put_file,
    resolve_alias,
)
from datetime import datetime, timedelta
from kim_scheduler.calendar.service import CalendarService
from kim_telegram.notify import TelegramNotifier
from kim_tools.web_search.client import WebSearchClient
from kim_tools.web_search.parser import create_voice_summary, normalize_results, summarize_results
from kim_voice.hotword.kim_hotword import HotwordConfig, KimHotwordListener
from kim_voice.stt.speech_to_text import KimSTT, STTConfig
from kim_voice.tts.voice import KimVoice


def get_vosk_model_path() -> str:
    """
    Получает путь к модели Vosk из переменной окружения или возвращает значение по умолчанию.

    Returns:
        str: Путь к модели Vosk
    """
    load_dotenv()

    # Проверяем переменную окружения
    model_path = os.getenv("VOSK_MODEL_PATH")

    if model_path:
        return model_path

    # Значение по умолчанию
    default_path = "models/vosk-ru"

    if not os.path.exists(default_path):
        logger.warning(
            f"Модель Vosk не найдена по пути по умолчанию: {default_path}. "
            f"Установите переменную окружения VOSK_MODEL_PATH"
        )

    return default_path


def extract_file_command(user_text: str) -> Optional[tuple[str, str, str]]:
    """
    Пытается распознать из user_text команду работы с файлами.

    Варианты команд:
    - "положи файл в документы" -> ("put", None, "documents")
    - "перемести то что я скачал на рабочий стол" -> ("move", "downloads", "desktop")
    - "перемести файл в загрузки" -> ("move", None, "downloads")

    Args:
        user_text: Текст пользователя

    Returns:
        Кортеж (action, source_alias, dest_alias) или None, если это не команда
        action: "put" или "move"
        source_alias: alias исходной директории (для move) или None
        dest_alias: alias директории назначения
    """
    user_text_lower = user_text.lower().strip()

    # Триггеры для "положить файл"
    put_triggers = [
        "положи файл",
        "скопируй файл",
        "положи в",
        "скопируй в",
    ]

    # Триггеры для "переместить файл"
    move_triggers = [
        "перемести",
        "перенеси",
        "перемести файл",
        "перенеси файл",
    ]

    # Определяем действие
    action = None
    trigger_pos = -1
    trigger_text = ""

    for trigger in put_triggers:
        if trigger in user_text_lower:
            action = "put"
            trigger_pos = user_text_lower.find(trigger)
            trigger_text = trigger
            break

    if action is None:
        for trigger in move_triggers:
            if trigger in user_text_lower:
                action = "move"
                trigger_pos = user_text_lower.find(trigger)
                trigger_text = trigger
                break

    if action is None:
        return None

    # Извлекаем текст после триггера
    after_trigger = user_text_lower[trigger_pos + len(trigger_text):].strip()

    # Пытаемся найти alias назначения
    dest_alias = None
    source_alias = None

    # Список возможных упоминаний директорий
    alias_keywords = {
        "documents": ["документы", "документ", "documents"],
        "desktop": ["рабочий стол", "desktop"],
        "downloads": ["загрузки", "загрузка", "скачал", "скачано", "downloads"],
    }

    # Ищем упоминания директорий в тексте
    found_aliases = []
    for alias, keywords in alias_keywords.items():
        for keyword in keywords:
            if keyword in after_trigger:
                found_aliases.append((alias, keyword))

    # Если найдено несколько упоминаний, первое - источник, второе - назначение
    if len(found_aliases) >= 2:
        source_alias = found_aliases[0][0]
        dest_alias = found_aliases[1][0]
    elif len(found_aliases) == 1:
        dest_alias = found_aliases[0][0]
        # Для move пытаемся определить источник из контекста
        if action == "move":
            # Если упоминается "скачал" или "загрузки" - это источник
            if any(word in after_trigger for word in ["скачал", "скачано", "загрузки", "загрузка"]):
                source_alias = "downloads"
            # Если упоминается "документы" - это может быть источник
            elif "документы" in after_trigger or "документ" in after_trigger:
                # Проверяем, не является ли это назначением
                if found_aliases[0][0] != "documents":
                    source_alias = "documents"

    # Если не нашли alias, пытаемся разрешить через resolve_alias
    if dest_alias is None:
        # Пытаемся найти последнее упоминание директории
        for alias, keywords in alias_keywords.items():
            for keyword in keywords:
                if keyword in after_trigger:
                    try:
                        resolved = resolve_alias(keyword)
                        dest_alias = resolved
                        break
                    except AliasNotFoundError:
                        continue
            if dest_alias:
                break

    if dest_alias is None:
        logger.debug(f"Не удалось определить alias назначения из текста: {user_text}")
        return None

    logger.debug(
        f"Распознана команда работы с файлами: action='{action}', "
        f"source_alias='{source_alias}', dest_alias='{dest_alias}'"
    )

    return (action, source_alias, dest_alias)


def extract_remind_command(user_text: str) -> Optional[tuple[str, int]]:
    """
    Пытается распознать из user_text команду создания напоминания с относительной датой.

    Варианты команд:
    - "напомни через 10 минут" -> ("текст напоминания", 10)
    - "напомни через час" -> ("текст напоминания", 60)
    - "напомни через 30 минут выпить воды" -> ("выпить воды", 30)

    Args:
        user_text: Текст пользователя

    Returns:
        Кортеж (title, minutes) или None, если это не команда
        title: Текст напоминания
        minutes: Количество минут до напоминания
    """
    import re
    user_text_lower = user_text.lower().strip()

    # Триггеры для напоминания
    remind_triggers = [
        "напомни через",
        "напомни мне через",
        "создай напоминание через",
        "поставь напоминание через",
    ]

    # Ищем триггер
    trigger_pos = -1
    trigger_text = ""

    for trigger in remind_triggers:
        if trigger in user_text_lower:
            trigger_pos = user_text_lower.find(trigger)
            trigger_text = trigger
            break

    if trigger_pos == -1:
        return None

    # Извлекаем текст после триггера
    after_trigger = user_text[trigger_pos + len(trigger_text):].strip()

    # Парсим относительное время
    # Паттерны: "10 минут", "30 минут", "1 час", "2 часа", "5 минут", "полчаса"
    time_patterns = [
        (r"(\d+)\s*минут", lambda m: int(m.group(1))),
        (r"(\d+)\s*минуты", lambda m: int(m.group(1))),
        (r"(\d+)\s*минуту", lambda m: int(m.group(1))),
        (r"(\d+)\s*час", lambda m: int(m.group(1)) * 60),
        (r"(\d+)\s*часа", lambda m: int(m.group(1)) * 60),
        (r"(\d+)\s*часов", lambda m: int(m.group(1)) * 60),
        (r"полчаса", lambda m: 30),
        (r"пол часа", lambda m: 30),
    ]

    minutes = None
    time_match_end = 0

    for pattern, converter in time_patterns:
        match = re.search(pattern, after_trigger.lower())
        if match:
            minutes = converter(match)
            time_match_end = match.end()
            break

    if minutes is None:
        logger.debug(f"Не удалось распознать время в команде напоминания: {after_trigger}")
        return None

    # Извлекаем текст напоминания (после времени)
    title = after_trigger[time_match_end:].strip()

    # Если текста нет, используем дефолтный
    if not title:
        title = "Напоминание"

    # Убираем лишние слова в начале
    title = re.sub(r"^(чтобы|что|о том|про то|что)\s+", "", title, flags=re.IGNORECASE).strip()

    logger.debug(
        f"Распознана команда напоминания: minutes={minutes}, title='{title}'"
    )

    return (title, minutes)


def extract_telegram_message_command(user_text: str) -> Optional[str]:
    """
    Пытается распознать из user_text команду отправки сообщения в Telegram.

    Варианты команд:
    - "отправь сообщение в телеграм: ..."
    - "отправь в телеграм: ..."
    - "скажи в телеграм: ..."

    Args:
        user_text: Текст пользователя

    Returns:
        Текст сообщения, который нужно отправить, либо None, если это не команда
    """
    user_text_lower = user_text.lower().strip()

    # Варианты триггеров
    triggers = [
        "отправь сообщение в телеграм",
        "отправь в телеграм",
        "скажи в телеграм",
        "отправь сообщение в телеграме",
        "отправь в телеграме",
        "скажи в телеграме",
    ]

    for trigger in triggers:
        if trigger in user_text_lower:
            # Ищем позицию триггера в оригинальном тексте (для сохранения регистра)
            trigger_lower = trigger.lower()
            idx = user_text_lower.find(trigger_lower)

            if idx != -1:
                # Всё после триггера
                after_trigger = user_text[idx + len(trigger):].strip()

                # Если есть двоеточие, берём текст после него
                if ":" in after_trigger:
                    parts = after_trigger.split(":", 1)
                    message_text = parts[1].strip()
                else:
                    # Если двоеточия нет, берём весь текст после триггера
                    message_text = after_trigger.strip()

                # Если текст сообщения не пустой, возвращаем его
                if message_text:
                    logger.debug(
                        f"Распознана команда отправки в Telegram: trigger='{trigger}', "
                        f"message='{message_text[:50]}...'"
                    )
                    return message_text

    return None


class VoiceRuntimeContext:
    """Контекст runtime-настроек для голосового ассистента."""

    def __init__(
        self,
        base_config: AppConfig,
        runtime_settings: RuntimeSettings,
        voice: KimVoice,
        llm_router: Optional[LLMRouter],
        telegram_notifier: Optional[TelegramNotifier],
    ) -> None:
        """
        Инициализирует контекст.

        Args:
            base_config: Базовая конфигурация из .env
            runtime_settings: Runtime-настройки
            voice: Объект синтезатора речи
            llm_router: Маршрутизатор LLM (может быть None в режиме local_only)
            telegram_notifier: Уведомитель Telegram (может быть None)
        """
        self.base_config = base_config
        self.runtime_settings = runtime_settings
        self.voice = voice
        self.llm_router = llm_router
        self.telegram_notifier = telegram_notifier
        self.merged_config = merge_config_with_runtime(base_config, runtime_settings)

    def apply_runtime_settings(self, new_settings: RuntimeSettings) -> None:
        """
        Применяет новые runtime-настройки.

        Args:
            new_settings: Новые runtime-настройки
        """
        old_settings = self.runtime_settings
        self.runtime_settings = new_settings

        # Пересобираем merged_config
        self.merged_config = merge_config_with_runtime(self.base_config, new_settings)

        # Логируем изменения
        changes = []
        if old_settings.local_only != new_settings.local_only and new_settings.local_only is not None:
            changes.append(f"local_only: {old_settings.local_only} → {new_settings.local_only}")
        if old_settings.tts_rate != new_settings.tts_rate and new_settings.tts_rate is not None:
            changes.append(f"tts_rate: {old_settings.tts_rate} → {new_settings.tts_rate}")
        if old_settings.tts_volume != new_settings.tts_volume and new_settings.tts_volume is not None:
            changes.append(f"tts_volume: {old_settings.tts_volume} → {new_settings.tts_volume}")
        if old_settings.model_fast != new_settings.model_fast and new_settings.model_fast is not None:
            changes.append(f"model_fast: {old_settings.model_fast} → {new_settings.model_fast}")
        if old_settings.model_smart != new_settings.model_smart and new_settings.model_smart is not None:
            changes.append(f"model_smart: {old_settings.model_smart} → {new_settings.model_smart}")
        if old_settings.token_budget_daily != new_settings.token_budget_daily and new_settings.token_budget_daily is not None:
            changes.append(f"token_budget_daily: {old_settings.token_budget_daily} → {new_settings.token_budget_daily}")
        if old_settings.voice_telegram_chat_id != new_settings.voice_telegram_chat_id and new_settings.voice_telegram_chat_id is not None:
            changes.append(f"voice_telegram_chat_id: {old_settings.voice_telegram_chat_id} → {new_settings.voice_telegram_chat_id}")

        if changes:
            logger.info(f"Runtime settings изменены: {', '.join(changes)}")
        else:
            logger.debug("Runtime settings перезагружены, изменений не обнаружено")

        # Применяем изменения к голосу
        if new_settings.tts_rate is not None:
            self.voice.set_rate(new_settings.tts_rate)
        if new_settings.tts_volume is not None:
            self.voice.set_volume(new_settings.tts_volume)

        # Проверяем изменения микрофона (логируем, но не применяем на лету)
        mic_changed = False
        if old_settings.mic_device_index != new_settings.mic_device_index and new_settings.mic_device_index is not None:
            mic_changed = True
        if old_settings.mic_sample_rate != new_settings.mic_sample_rate and new_settings.mic_sample_rate is not None:
            mic_changed = True
        if old_settings.mic_chunk_size != new_settings.mic_chunk_size and new_settings.mic_chunk_size is not None:
            mic_changed = True

        if mic_changed:
            logger.warning(
                "Настройки микрофона изменены в runtime_settings.json. "
                "Для полного применения этих изменений может потребоваться перезапуск ассистента."
            )


def main() -> None:
    """Основная функция запуска голосового ассистента."""
    # Загрузка конфигурации
    base_config = load_config()

    # Инициализация логирования
    init_logger(base_config)

    # Инициализация runtime-настроек
    runtime_settings_path = os.getenv(
        "RUNTIME_SETTINGS_PATH", "data/runtime_settings.json"
    )
    runtime_store = RuntimeSettingsStore(runtime_settings_path)
    
    try:
        runtime_settings = runtime_store.load()
        logger.info(f"Runtime settings loaded from {runtime_settings_path}")
        profile_name = runtime_settings.profile or "custom"
        mode_name = runtime_settings.mode or "custom"
        scenario_name = runtime_settings.scenario or "none"
        logger.info(f"Voice runtime profile: {profile_name}")
        logger.info(f"Voice runtime mode: {mode_name}")
        logger.info(f"Voice runtime scenario: {scenario_name}")
    except Exception as e:
        logger.warning(f"Failed to load runtime settings: {e}, using defaults")
        runtime_settings = RuntimeSettings()
        logger.info("Voice runtime profile: custom (defaults)")
        logger.info("Voice runtime mode: custom (defaults)")
        logger.info("Voice runtime scenario: none (defaults)")

    # Объединяем базовую конфигурацию с runtime-настройками
    config = merge_config_with_runtime(base_config, runtime_settings)

    logger.info("=" * 60)
    logger.info("Запуск голосового ассистента «Ким»")
    logger.info("=" * 60)

    # Проверка наличия VOSK_MODEL_PATH
    model_path = get_vosk_model_path()

    if not model_path or not os.path.exists(model_path):
        error_msg = (
            f"Модель Vosk не найдена!\n"
            f"Пожалуйста:\n"
            f"1. Скачайте модель Vosk (например, русскую) с https://alphacephei.com/vosk/models\n"
            f"2. Распакуйте её в папку models/vosk-ru\n"
            f"3. Или укажите путь через переменную окружения VOSK_MODEL_PATH в .env"
        )
        logger.error(error_msg)
        print(f"\n❌ ОШИБКА: {error_msg}\n")
        sys.exit(1)

    logger.info(f"Используется модель Vosk: {model_path}")

    # Проверка наличия OPENROUTER_API_KEY (только если не включён режим local_only)
    if not config.local_only:
        if not config.openrouter_api_key:
            error_msg = (
                "OPENROUTER_API_KEY не установлен!\n"
                "Пожалуйста, добавьте OPENROUTER_API_KEY в файл .env\n"
                "Или включите режим LOCAL_ONLY=1 для работы без LLM"
            )
            logger.error(error_msg)
            print(f"\n❌ ОШИБКА: {error_msg}\n")
            sys.exit(1)
    else:
        logger.info("Режим LOCAL_ONLY включён — LLM не будет использоваться")

    try:
        # Загрузка дополнительных настроек из переменных окружения
        load_dotenv()
        stt_use_vad = os.getenv("STT_USE_VAD", "0").lower() in ("1", "true", "yes", "on")
        stt_vad_aggressiveness = int(os.getenv("STT_VAD_AGGRESSIVENESS", "2"))
        hotword_adaptive_threshold = os.getenv("HOTWORD_ADAPTIVE_THRESHOLD", "1").lower() in ("1", "true", "yes", "on")
        
        # Логируем используемое устройство ввода с именем
        device_name = "по умолчанию"
        if config.mic_device_index is not None:
            try:
                import sounddevice as sd
                device_info = sd.query_devices(config.mic_device_index)
                device_name = device_info['name']
                logger.info(f"Используется микрофон [{config.mic_device_index}]: {device_name}")
            except Exception as e:
                logger.warning(f"Не удалось получить имя устройства {config.mic_device_index}: {e}")
                device_name = f"устройство {config.mic_device_index}"
                logger.info(f"Используется микрофон с индексом: {config.mic_device_index}")
        else:
            try:
                import sounddevice as sd
                default_input = sd.default.device[0]
                if default_input is not None:
                    device_info = sd.query_devices(default_input)
                    device_name = device_info['name']
                    logger.info(f"Используется микрофон по умолчанию [{default_input}]: {device_name}")
            except Exception:
                logger.info("Используется микрофон по умолчанию")
        
        # Загрузка параметров hotword из переменных окружения
        min_hotword_confidence = float(os.getenv("HOTWORD_MIN_CONFIDENCE", "0.5"))
        min_chars_in_utterance = int(os.getenv("HOTWORD_MIN_CHARS", "2"))
        
        # Создание конфигурации hotword с настройками микрофона из config
        hotword_config = HotwordConfig(
            model_path=model_path,
            sample_rate=config.mic_sample_rate,
            chunk_size=config.mic_chunk_size,
            confidence_threshold=0.7,
            debounce_seconds=1.2,
            min_hotword_confidence=min_hotword_confidence,
            min_chars_in_utterance=min_chars_in_utterance,
            adaptive_threshold=hotword_adaptive_threshold,
            device_index=config.mic_device_index,
        )

        # Создание слушателя hotword
        logger.info("Инициализация детектора hotword...")
        listener = KimHotwordListener(hotword_config)

        # Создание конфигурации STT с настройками микрофона из config
        stt_config = STTConfig(
            model_path=model_path,
            sample_rate=config.mic_sample_rate,
            chunk_size=config.mic_chunk_size,
            max_phrase_duration=10.0,
            silence_timeout=1.5,
            use_vad=stt_use_vad,
            vad_aggressiveness=stt_vad_aggressiveness,
            device_index=config.mic_device_index,
        )

        # Создание распознавателя речи
        logger.info("Инициализация распознавателя речи (STT)...")
        stt = KimSTT(stt_config)

        # Создание синтезатора речи
        logger.info("Инициализация синтезатора речи (TTS)...")
        # rate: для COM это -10 до 10, где 0 - нормальная скорость
        # 2-4 делает речь немного быстрее и более живой, но не слишком быстро
        tts_rate = runtime_settings.tts_rate if runtime_settings.tts_rate is not None else 3
        tts_volume = runtime_settings.tts_volume if runtime_settings.tts_volume is not None else 100
        voice = KimVoice(rate=tts_rate, volume=tts_volume)

        # Создание клиента веб-поиска
        web_search_client = WebSearchClient(
            api_key=config.serpapi_key,
            timeout=10,
        )
        logger.info("WebSearchClient инициализирован")

        # Создание сервиса календаря для напоминаний
        from kim_scheduler.calendar.storage import CalendarStorage
        calendar_storage = CalendarStorage(config.reminders_db_path)
        calendar_service = CalendarService(calendar_storage)
        logger.info("CalendarService инициализирован")

        # Создание TelegramNotifier для голосовых отправок
        telegram_notifier = None
        if config.voice_telegram_chat_id is not None and config.telegram_bot_token:
            try:
                telegram_notifier = TelegramNotifier(
                    bot_token=config.telegram_bot_token,
                    chat_id=config.voice_telegram_chat_id,  # Для совместимости, но будем использовать send_text
                )
                logger.info(
                    f"Voice → Telegram: TelegramNotifier инициализирован для "
                    f"chat_id={config.voice_telegram_chat_id}"
                )
            except Exception as e:
                logger.warning(f"Voice → Telegram: ошибка инициализации TelegramNotifier: {e}")
                telegram_notifier = None
        else:
            if config.voice_telegram_chat_id is None:
                logger.info(
                    "Voice → Telegram: VOICE_TELEGRAM_CHAT_ID не задан, "
                    "голосовые отправки в Telegram недоступны"
                )
            if not config.telegram_bot_token:
                logger.info(
                    "Voice → Telegram: BOT_TOKEN не задан, "
                    "голосовые отправки в Telegram недоступны"
                )

        # Создание LLM-клиента и маршрутизатора (только если не local_only)
        llm_client = None
        llm_router = None

        if not config.local_only:
            logger.info("Инициализация LLM-клиента...")
            llm_client = OpenRouterClient(config)
            llm_router = LLMRouter(config, llm_client)
            
            # Регистрируем инструмент веб-поиска в LLMRouter
            from kim_tools.web_search.tools import WebSearchTool
            web_search_tool = WebSearchTool(web_search_client)
            llm_router.register_tool(web_search_tool)
            logger.info("Инструмент web_search зарегистрирован в LLMRouter")
        else:
            logger.info("LLM-клиент пропущен (режим LOCAL_ONLY)")

        # Создание контекста runtime-настроек
        context = VoiceRuntimeContext(
            base_config=base_config,
            runtime_settings=runtime_settings,
            voice=voice,
            llm_router=llm_router,
            telegram_notifier=telegram_notifier,
        )

        logger.info("Все компоненты инициализированы")

        # Вспомогательная функция для синхронного вызова LLM
        def ask_llm_sync(user_text: str, router: LLMRouter) -> str:
            """
            Синхронно отправляет запрос в LLM и возвращает ответ.

            Args:
                user_text: Текст вопроса пользователя

            Returns:
                str: Текст ответа от LLM или сообщение об ошибке
            """
            logger.info(f"Вопрос пользователя: {user_text}")

            # Формируем сообщения
            messages = [
                get_system_prompt(),
                {"role": "user", "content": user_text},
            ]

            # Асинхронный вызов через asyncio.run
            async def _run_llm() -> str:
                try:
                    response = await router.run(messages)
                    return response
                except BudgetExceededError as e:
                    logger.warning(f"Превышен лимит токенов: {e}")
                    return "На сегодня исчерпан лимит запросов, попробуйте завтра."
                except LLMError as e:
                    logger.error(f"Ошибка LLM: {e}")
                    return "Сейчас не могу ответить, попробуйте позже."

            try:
                answer = asyncio.run(_run_llm())
                logger.info(f"Ответ LLM: {answer[:100]}...")
                return answer
            except Exception as e:
                logger.exception(f"Неожиданная ошибка при запросе к LLM: {e}")
                return "Произошла ошибка, попробуйте позже."

        # Функция для получения локального ответа
        def get_local_response(user_text: str) -> str:
            """
            Формирует локальный ответ без обращения к LLM.

            Args:
                user_text: Текст пользователя

            Returns:
                str: Локальный ответ
            """
            text_lower = user_text.lower()

            if any(word in text_lower for word in ["привет", "здравствуй", "добрый"]):
                return "Привет! Сейчас я работаю в локальном режиме и не обращаюсь к интернету."
            elif any(word in text_lower for word in ["время", "который час"]):
                from datetime import datetime
                current_time = datetime.now().strftime("%H:%M")
                return f"Сейчас {current_time}."
            else:
                return "Сейчас включён режим только локально, я не обращаюсь к ИИ-модели."

        # Пороги для мягкого подтверждения
        CONFIRMATION_CONF_THRESHOLD = 0.75  # если уверенность выше - не спрашиваем
        CONFIRMATION_LENGTH_THRESHOLD = 25  # если фраза длиннее - спрашиваем

        # Определение callback при обнаружении hotword
        def on_hotword_triggered() -> None:
            """Обработчик срабатывания hotword."""
            # Проверяем и перезагружаем runtime-настройки, если файл изменился
            new_settings = runtime_store.reload_if_changed()
            if new_settings is not None:
                context.apply_runtime_settings(new_settings)
                # Обновляем llm_router, если он есть и настройки изменились
                if context.llm_router is not None:
                    # Обновляем конфигурацию в LLMRouter (если он поддерживает это)
                    # Для простоты пересоздаём клиент и роутер, если изменились модели/лимиты
                    if (
                        new_settings.model_fast is not None
                        or new_settings.model_smart is not None
                        or new_settings.token_budget_daily is not None
                    ):
                        logger.info("Обновление LLM-конфигурации из runtime-настроек")
                        try:
                            current_config = context.merged_config
                            new_client = OpenRouterClient(current_config)
                            new_router = LLMRouter(current_config, new_client)
                            # Регистрируем инструмент веб-поиска
                            from kim_tools.web_search.tools import WebSearchTool
                            web_search_tool = WebSearchTool(web_search_client)
                            new_router.register_tool(web_search_tool)
                            context.llm_router = new_router
                        except Exception as e:
                            logger.warning(f"Не удалось обновить LLM-конфигурацию: {e}")

            logger.info(">>> Hotword «Ким» активирован!")

            # Озвучиваем ответ (используем voice из context)
            context.voice.speak("Да, слушаю.")

            # Получаем фразу с уверенностью для мягкого подтверждения
            result = stt.listen_once_with_confidence()
            
            if result is None:
                # Если не удалось распознать, пробуем с обычным методом
                user_text = stt.listen_with_retries(max_retries=2)
                if not user_text or not user_text.strip():
                    logger.warning("Речь не распознана после нескольких попыток")
                    context.voice.speak("Не расслышала, повторите позже.")
                    return
                user_text_final = user_text
                avg_conf = 1.0  # По умолчанию полная уверенность
            else:
                user_text_final, avg_conf = result

            logger.info(f"Распознанная фраза: '{user_text_final}', уверенность: {avg_conf:.2f}")
            print(f"\n>>> Распознано: {user_text_final}\n")

            # Определяем, нужно ли подтверждение
            needs_confirmation = (
                avg_conf < CONFIRMATION_CONF_THRESHOLD or
                len(user_text_final) >= CONFIRMATION_LENGTH_THRESHOLD
            )

            if not needs_confirmation:
                logger.info(
                    f"Подтверждение не требуется "
                    f"(уверенность={avg_conf:.2f} >= {CONFIRMATION_CONF_THRESHOLD}, "
                    f"длина={len(user_text_final)} < {CONFIRMATION_LENGTH_THRESHOLD})"
                )
                user_text = user_text_final
            else:
                # Озвучиваем подтверждение распознанной фразы
                logger.info(
                    f"Требуется подтверждение "
                    f"(уверенность={avg_conf:.2f} < {CONFIRMATION_CONF_THRESHOLD} "
                    f"или длина={len(user_text_final)} >= {CONFIRMATION_LENGTH_THRESHOLD})"
                )
                context.voice.speak(f"Кажется, вы сказали: {user_text_final}. Всё верно?")

                # Слушаем подтверждение пользователя (короткий ответ)
                confirmation_text = stt.listen_once_for_confirmation(min_chars=2)

                # Обрабатываем подтверждение
                if confirmation_text:
                    confirmation_lower = confirmation_text.lower()
                    logger.info(f"Ответ на подтверждение: '{confirmation_text}'")

                    # Если пользователь сказал "нет"
                    if any(word in confirmation_lower for word in ["нет", "неверно", "не так", "неправильно"]):
                        logger.info("Пользователь отклонил распознанную фразу, просим повторить")
                        context.voice.speak("Хорошо, повторите, пожалуйста.")

                        # Повторная попытка распознавания
                        result_retry = stt.listen_once_with_confidence()
                        if result_retry is None:
                            user_text = stt.listen_with_retries(max_retries=2)
                            if not user_text or not user_text.strip():
                                logger.warning("Речь не распознана после повторной попытки")
                                context.voice.speak("Не расслышала, повторите позже.")
                                return
                            user_text = user_text
                        else:
                            user_text, _ = result_retry

                        logger.info(f"Повторно распознанная фраза: '{user_text}'")
                        print(f"\n>>> Распознано: {user_text}\n")
                    else:
                        # Если "да" или неясный ответ - используем первоначальную фразу
                        logger.info("Подтверждение получено, используем первоначальную фразу")
                        user_text = user_text_final
                else:
                    # Если подтверждение не распознано - используем первоначальную фразу
                    logger.info("Подтверждение не распознано, используем первоначальную фразу")
                    user_text = user_text_final

            # Проверяем, является ли это командой веб-поиска
            user_text_lower = user_text.lower()
            web_search_triggers = [
                "найди",
                "поищи",
                "что в интернете про",
                "какие новости про",
                "найди в интернете",
                "поищи в интернете",
            ]
            
            is_web_search = False
            search_query = None
            
            for trigger in web_search_triggers:
                if user_text_lower.startswith(trigger):
                    is_web_search = True
                    # Извлекаем запрос после триггера
                    search_query = user_text[len(trigger):].strip()
                    break
            
            # Если это команда веб-поиска
            if is_web_search and search_query:
                logger.info(f"Обнаружена команда веб-поиска: query='{search_query}'")
                context.voice.speak("Ищу информацию в интернете...")
                
                try:
                    # Выполняем поиск асинхронно (через asyncio.run, как и LLM)
                    async def _run_web_search() -> list:
                        return await web_search_client.search(search_query, 5)
                    
                    results = asyncio.run(_run_web_search())
                    
                    if results:
                        normalized = normalize_results(results, limit=5)
                        # Используем короткую выжимку для голосового вывода
                        voice_summary = create_voice_summary(normalized)
                        answer = voice_summary
                    else:
                        answer = "К сожалению, по вашему запросу ничего не найдено."
                    
                    logger.info("Веб-поиск выполнен успешно")
                    
                except Exception as e:
                    logger.exception(f"Ошибка веб-поиска: {e}")
                    answer = "Извините, произошла ошибка при поиске в интернете."
                
                # Озвучиваем ответ
                logger.info("Озвучивание результата поиска...")
                context.voice.speak(answer)
                return

            # Проверяем, является ли это командой работы с файлами
            file_command = extract_file_command(user_text)

            if file_command is not None:
                action, source_alias, dest_alias = file_command
                logger.info(f"Обнаружена команда работы с файлами: action='{action}', source_alias='{source_alias}', dest_alias='{dest_alias}'")

                try:
                    if action == "put":
                        # Для put нужно найти файл (последний скачанный или спросить у пользователя)
                        context.voice.speak("Какой файл нужно скопировать? Укажите путь к файлу.")
                        file_path_text = stt.listen_with_retries(max_retries=2)
                        
                        if not file_path_text or not file_path_text.strip():
                            context.voice.speak("Не расслышала путь к файлу. Попробуйте позже.")
                            return

                        from pathlib import Path
                        source_path = Path(file_path_text.strip())
                        result_path = put_file(source_path, dest_alias)
                        context.voice.speak(f"Файл успешно скопирован в {dest_alias}.")
                        logger.info(f"Файл скопирован: {source_path} -> {result_path}")

                    elif action == "move":
                        # Для move определяем исходный файл
                        source_path = None

                        if source_alias:
                            # Если указан источник (например, "то что я скачал"), ищем последний файл
                            from kim_desktop.files.file_manager import find_latest_file
                            source_path = find_latest_file(source_alias)
                            
                            if source_path is None:
                                context.voice.speak(f"В {source_alias} не найдено файлов для перемещения.")
                                return
                        else:
                            # Если источник не указан, спрашиваем у пользователя
                            context.voice.speak("Какой файл нужно переместить? Укажите путь к файлу.")
                            file_path_text = stt.listen_with_retries(max_retries=2)
                            
                            if not file_path_text or not file_path_text.strip():
                                context.voice.speak("Не расслышала путь к файлу. Попробуйте позже.")
                                return

                            from pathlib import Path
                            source_path = Path(file_path_text.strip())

                        result_path = move_file(source_path, dest_alias)
                        context.voice.speak(f"Файл успешно перемещён в {dest_alias}.")
                        logger.info(f"Файл перемещён: {source_path} -> {result_path}")

                except AliasNotFoundError as e:
                    context.voice.speak(f"Директория не найдена: {str(e)}")
                except (FileManagerError, PathTraversalError) as e:
                    context.voice.speak(f"Ошибка при работе с файлом: {str(e)}")
                except Exception as e:
                    logger.exception(f"Ошибка при обработке файловой команды: {e}")
                    context.voice.speak("Произошла ошибка при работе с файлом. Попробуйте позже.")

                return  # Выходим, не продолжаем обычную логику

            # Проверяем, является ли это командой создания напоминания
            remind_command = extract_remind_command(user_text)

            if remind_command is not None:
                title, minutes = remind_command
                logger.info(f"Обнаружена команда напоминания: minutes={minutes}, title='{title}'")

                try:
                    # Вычисляем время события (текущее время + minutes минут)
                    dt_utc = datetime.utcnow() + timedelta(minutes=minutes)

                    # Создаём событие
                    event = calendar_service.create_event(
                        user_id=0,  # В голосовом режиме user_id=0 (локальный пользователь)
                        title=title,
                        dt_utc=dt_utc,
                        remind_before_minutes=10,  # По умолчанию напоминать за 10 минут
                    )

                    # Форматируем время для голосового вывода
                    time_str = dt_utc.strftime("%H:%M")
                    response = f"Напоминание создано на {time_str}. {title}."
                    context.voice.speak(response)
                    logger.info(f"Напоминание создано через голос: id={event.id}, title='{title}', minutes={minutes}")

                except Exception as e:
                    logger.exception(f"Ошибка при создании напоминания: {e}")
                    context.voice.speak("Произошла ошибка при создании напоминания. Попробуйте позже.")

                return  # Выходим, не продолжаем обычную логику

            # Проверяем, является ли это командой отправки в Telegram
            telegram_message = extract_telegram_message_command(user_text)

            if telegram_message is not None and context.telegram_notifier is not None:
                logger.info(f"Обнаружена команда отправки в Telegram: message='{telegram_message[:50]}...'")

                # Проверяем, что chat_id настроен (используем актуальный config из context)
                current_config = context.merged_config
                if current_config.voice_telegram_chat_id is None:
                    logger.warning("Voice → Telegram: voice_telegram_chat_id не установлен")
                    context.voice.speak("Чат для отправки в Telegram не настроен.")
                    return

                # Ким подтверждает текст
                confirmation_text = f"Отправить в Telegram: «{telegram_message}»?"
                logger.info(f"Voice → Telegram: подтверждение отправки: '{telegram_message}'")
                context.voice.speak(confirmation_text)

                # Слушаем подтверждение пользователя
                try:
                    confirmation_response = stt.listen_once_for_confirmation(min_chars=2)
                    
                    if confirmation_response:
                        confirmation_lower = confirmation_response.lower()
                        logger.info(f"Voice → Telegram: ответ на подтверждение: '{confirmation_response}'")

                        # Если пользователь сказал "нет"
                        if any(word in confirmation_lower for word in ["нет", "неверно", "не так", "неправильно", "отмена"]):
                            logger.info("Voice → Telegram: пользователь отменил отправку")
                            context.voice.speak("Хорошо, не отправляю.")
                            return

                        # Если "да" или ответ пустой/неуверенный, считаем что отправка разрешена
                        # (по умолчанию разрешаем, если нет явного отказа)
                        logger.info("Voice → Telegram: подтверждение получено, отправляю сообщение")

                        # Отправка в Telegram асинхронно
                        try:
                            async def _send_telegram_message() -> None:
                                await context.telegram_notifier.send_text(
                                    current_config.voice_telegram_chat_id,
                                    telegram_message
                                )

                            asyncio.run(_send_telegram_message())
                            logger.info(
                                f"Voice → Telegram: сообщение успешно отправлено в "
                                f"chat_id={current_config.voice_telegram_chat_id}"
                            )
                            context.voice.speak("Отправила сообщение в Telegram.")
                        except Exception as e:
                            logger.exception(f"Voice → Telegram: ошибка отправки сообщения: {e}")
                            context.voice.speak(
                                "Не получилось отправить сообщение в Telegram. "
                                "Проверьте соединение и настройки."
                            )
                    else:
                        # Если подтверждение не распознано, не отправляем (безопасность)
                        logger.warning("Voice → Telegram: подтверждение не распознано, отмена отправки")
                        context.voice.speak("Не расслышала подтверждение. Отправка отменена.")

                except Exception as e:
                    logger.exception(f"Voice → Telegram: ошибка при обработке подтверждения: {e}")
                    context.voice.speak("Произошла ошибка при обработке команды.")
                
                return  # Выходим, не продолжаем обычную логику

            # Ветвление по режиму local_only (используем актуальный config из context)
            current_config = context.merged_config
            if current_config.local_only:
                logger.info("Использование локального режима (без LLM)")
                answer = get_local_response(user_text)
                logger.info(f"Локальный ответ: {answer}")
            else:
                # Получаем ответ от LLM
                logger.info("Отправка запроса в LLM...")
                # Используем llm_router из context
                current_llm_router = context.llm_router
                if current_llm_router is None:
                    logger.warning("LLM-роутер недоступен, используем локальный ответ")
                    answer = get_local_response(user_text)
                else:
                    answer = ask_llm_sync(user_text, current_llm_router)

            # Озвучиваем ответ (используем voice из context)
            logger.info("Озвучивание ответа...")
            context.voice.speak(answer)

        # Запуск прослушивания
        mode_info = " (режим только локально)" if context.merged_config.local_only else ""
        logger.info("\n" + "=" * 60)
        logger.info(f"Голосовой ассистент готов к работе!{mode_info}")
        logger.info("Произнесите «Ким» для активации")
        logger.info("После активации задайте вопрос голосом")
        logger.info("Для остановки нажмите Ctrl+C")
        logger.info("=" * 60 + "\n")

        listener.listen(on_hotword_triggered)

    except KeyboardInterrupt:
        logger.info("\nОстановка голосового ассистента по запросу пользователя...")
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        print(f"\n❌ ОШИБКА: Файл не найден: {e}\n")
        sys.exit(1)
    except RuntimeError as e:
        error_msg = str(e)
        if "Vosk" in error_msg or "модель" in error_msg.lower():
            logger.exception(f"Voice assistant crashed: {e}")
            print(
                f"\n❌ Голосовой ассистент не смог запуститься.\n"
                f"Проверьте модель Vosk и путь к ней в VOSK_MODEL_PATH.\n"
                f"Детали: {error_msg}\n"
            )
        else:
            logger.exception(f"Voice assistant crashed: {e}")
            print(
                f"\n❌ Голосовой ассистент не смог запуститься.\n"
                f"Проверьте микрофон, модель Vosk и настройки.\n"
                f"Детали: {error_msg}\n"
            )
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Voice assistant crashed: {e}")
        print(
            f"\n❌ Голосовой ассистент не смог запуститься.\n"
            f"Проверьте микрофон, модель Vosk и настройки.\n"
            f"Детали: {str(e)}\n"
        )
        sys.exit(1)
    finally:
        # Закрываем TelegramNotifier при завершении
        if 'telegram_notifier' in locals() and telegram_notifier:
            try:
                asyncio.run(telegram_notifier.close())
                logger.debug("Voice → Telegram: TelegramNotifier закрыт")
            except Exception as e:
                logger.warning(f"Voice → Telegram: ошибка закрытия TelegramNotifier: {e}")


if __name__ == "__main__":
    main()
