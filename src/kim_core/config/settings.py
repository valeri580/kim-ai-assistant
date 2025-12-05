"""Конфигурация приложения."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


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

    config = AppConfig(
        mode=os.getenv("MODE", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        telegram_bot_token=os.getenv("BOT_TOKEN"),
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
    )

    config.validate()

    return config

