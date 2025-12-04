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

    config = AppConfig(
        mode=os.getenv("MODE", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        telegram_bot_token=os.getenv("BOT_TOKEN"),
        model_fast=os.getenv("MODEL_FAST", "openrouter/fast"),
        model_smart=os.getenv("MODEL_SMART", "openrouter/smart"),
        token_budget_daily=int(os.getenv("TOKEN_BUDGET_DAILY", "50000")),
    )

    config.validate()

    return config

