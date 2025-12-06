"""Конфигурация приложения."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

from kim_core.secret_store import load_secret_from_env_or_keyring


@dataclass
class AppConfig:
    """Конфигурация приложения."""

    mode: str
    log_level: str
    openrouter_api_key: Optional[str]
    telegram_bot_token: Optional[str]
    model_fast: str
    model_smart: str
    token_budget_daily: int
    local_only: bool = False
    # Пороги для диагностики системы
    cpu_warn: float = 85.0
    ram_warn: float = 90.0
    disk_warn: float = 90.0
    temp_warn: Optional[float] = None
    alerts_chat_id: Optional[int] = None
    diagnostics_interval_seconds: int = 60
    # Настройки микрофона
    mic_device_index: Optional[int] = None
    mic_sample_rate: int = 16000
    mic_chunk_size: int = 4000
    # Настройки напоминаний и календаря
    reminders_db_path: str = "data/calendar.db"
    reminders_interval_seconds: int = 60
    # Настройки веб-поиска
    serpapi_key: Optional[str] = None
    web_search_max_results: int = 5
    # Настройки работы с файлами
    file_whitelist_dirs: Optional[list[str]] = None
    file_max_size_mb: int = 10
    file_summary_max_chars: int = 20000
    # Настройки голосовых отправок в Telegram
    voice_telegram_chat_id: Optional[int] = None
    # Таймаут для LLM-запросов (в секундах)
    llm_timeout_seconds: float = 15.0

    def validate(self) -> None:
        """Валидация конфигурации для режима prod."""
        if self.mode == "prod":
            if not self.openrouter_api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY обязателен для режима prod"
                )
            if not self.telegram_bot_token:
                raise ValueError(
                    "BOT_TOKEN обязателен для режима prod"
                )


def load_config() -> AppConfig:
    """
    Загружает конфигурацию из переменных окружения.

    Returns:
        AppConfig: Объект конфигурации

    Raises:
        ValueError: Если в режиме prod отсутствуют обязательные переменные
    """
    load_dotenv()

    # Преобразование LOCAL_ONLY в bool
    local_only_str = os.getenv("LOCAL_ONLY", "0").lower().strip()
    local_only = local_only_str in ("1", "true", "yes", "on")

    # Пороги диагностики системы
    def get_float_or_default(key: str, default: float) -> float:
        """Получает float из переменной окружения или возвращает default."""
        value = os.getenv(key)
        if value:
            try:
                return float(value)
            except ValueError:
                pass
        return default

    def get_float_or_none(key: str) -> Optional[float]:
        """Получает float из переменной окружения или None."""
        value = os.getenv(key)
        if value and value.strip():
            try:
                return float(value)
            except ValueError:
                pass
        return None

    def get_int_or_default(key: str, default: int) -> int:
        """Получает int из переменной окружения или возвращает default."""
        value = os.getenv(key)
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return default

    def get_int_or_none(key: str) -> Optional[int]:
        """Получает int из переменной окружения или None."""
        value = os.getenv(key)
        if value and value.strip():
            try:
                return int(value)
            except ValueError:
                pass
        return None

    def get_str_or_default(key: str, default: str) -> str:
        """Получает строку из переменной окружения или возвращает default."""
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
        return default

    def parse_file_whitelist_dirs() -> Optional[list[str]]:
        """
        Парсит переменную окружения FILE_WHITELIST_DIRS.

        Ожидает строку с путями, разделёнными ';' или ':'.

        Returns:
            Список путей или None, если переменная не задана
        """
        value = os.getenv("FILE_WHITELIST_DIRS")
        if not value or not value.strip():
            return None

        # Разделяем по ';' или ':' (поддержка разных форматов)
        # Проверяем наличие разделителя, но учитываем Windows-пути с ':'
        if ";" in value:
            paths = value.split(";")
        elif ":" in value:
            # Для Windows-путей (C:\...) используем более умную логику
            # Просто разделяем по ':', но только если это не Windows-путь
            parts = value.split(":")
            if len(parts) == 2 and len(parts[0]) == 1:
                # Вероятно, это Windows-путь вида C:\path
                paths = [value]
            else:
                paths = parts
        else:
            paths = [value]

        # Нормализуем пути (убираем пробелы, фильтруем пустые)
        normalized_paths = [p.strip() for p in paths if p.strip()]

        if not normalized_paths:
            return None

        return normalized_paths

    # Загружаем секреты из переменных окружения или keyring
    # Если секрет найден в окружении - сохраняем в keyring и стираем из процесса
    openrouter_api_key = load_secret_from_env_or_keyring("OPENROUTER_API_KEY", "openrouter_api_key")
    telegram_bot_token = load_secret_from_env_or_keyring("BOT_TOKEN", "telegram_bot_token")

    config = AppConfig(
        mode=os.getenv("MODE", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        openrouter_api_key=openrouter_api_key,
        telegram_bot_token=telegram_bot_token,
        model_fast=os.getenv("MODEL_FAST", "openai/gpt-3.5-turbo"),
        model_smart=os.getenv("MODEL_SMART", "openai/gpt-4-turbo"),
        token_budget_daily=int(os.getenv("TOKEN_BUDGET_DAILY", "50000")),
        local_only=local_only,
        cpu_warn=get_float_or_default("CPU_WARN", 85.0),
        ram_warn=get_float_or_default("RAM_WARN", 90.0),
        disk_warn=get_float_or_default("DISK_WARN", 90.0),
        temp_warn=get_float_or_none("TEMP_WARN"),
        alerts_chat_id=get_int_or_none("ALERTS_CHAT_ID"),
        diagnostics_interval_seconds=get_int_or_default("DIAGNOSTICS_INTERVAL_SECONDS", 60),
        mic_device_index=get_int_or_none("MIC_DEVICE_INDEX"),
        mic_sample_rate=get_int_or_default("MIC_SAMPLE_RATE", 16000),
        mic_chunk_size=get_int_or_default("MIC_CHUNK_SIZE", 4000),
        reminders_db_path=get_str_or_default("REMINDERS_DB_PATH", "data/calendar.db"),
        reminders_interval_seconds=get_int_or_default("REMINDERS_INTERVAL_SECONDS", 60),
        serpapi_key=os.getenv("SERPAPI_KEY"),
        web_search_max_results=get_int_or_default("WEB_SEARCH_MAX_RESULTS", 5),
        file_whitelist_dirs=parse_file_whitelist_dirs(),
        file_max_size_mb=get_int_or_default("FILE_MAX_SIZE_MB", 10),
        file_summary_max_chars=get_int_or_default("FILE_SUMMARY_MAX_CHARS", 20000),
        voice_telegram_chat_id=get_int_or_none("VOICE_TELEGRAM_CHAT_ID"),
        llm_timeout_seconds=get_float_or_default("LLM_TIMEOUT_SECONDS", 15.0),
    )

    config.validate()

    return config

