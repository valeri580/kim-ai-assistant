"""Модели для панели настроек."""

from typing import Optional

from pydantic import BaseModel, Field

from kim_core.config.runtime import RuntimeSettings


# Список допустимых профилей
PROFILES = ["quality", "balanced", "performance"]

# Список допустимых режимов работы
MODES = ["voice_assistant", "telegram_only", "offline"]

# Готовые сценарии (объединяют mode + profile + дополнительные настройки)
SCENARIOS = {
    "home_voice_assistant": {
        "label": "Домашний голосовой ассистент",
        "description": "Голосовой ассистент + Telegram + онлайн LLM с упором на качество.",
        "mode": "voice_assistant",
        "profile": "quality",
    },
    "light_telegram_helper": {
        "label": "Лёгкий Telegram-помощник",
        "description": "Только Telegram-бот, без голосового интерфейса, с экономным использованием LLM.",
        "mode": "telegram_only",
        "profile": "performance",
    },
    "offline_desktop_assistant": {
        "label": "Полностью офлайн настольный ассистент",
        "description": "Максимально локальный режим, без LLM и интернет-поиска.",
        "mode": "offline",
        "profile": "balanced",
    },
}


class RuntimeSettingsUpdate(BaseModel):
    """Модель для частичного обновления runtime-настроек."""

    scenario: Optional[str] = Field(None, description="Имя сценария для применения")
    mode: Optional[str] = Field(None, description="Режим работы (voice_assistant, telegram_only, offline)")
    profile: Optional[str] = Field(None, description="Имя профиля для применения")
    enable_voice_assistant: Optional[bool] = Field(None, description="Включить голосовой ассистент")
    enable_web_search: Optional[bool] = Field(None, description="Включить веб-поиск")
    local_only: Optional[bool] = Field(None, description="Режим только локально (без LLM)")
    tts_rate: Optional[int] = Field(None, description="Скорость речи (-10 до 10 для COM)")
    tts_volume: Optional[int] = Field(None, description="Громкость (0-100)")
    model_fast: Optional[str] = Field(None, description="Быстрая модель LLM")
    model_smart: Optional[str] = Field(None, description="Умная модель LLM")
    token_budget_daily: Optional[int] = Field(None, description="Дневной лимит токенов")
    mic_device_index: Optional[int] = Field(None, description="Индекс микрофона")
    mic_sample_rate: Optional[int] = Field(None, description="Частота дискретизации микрофона")
    mic_chunk_size: Optional[int] = Field(None, description="Размер чанка микрофона")
    voice_telegram_chat_id: Optional[int] = Field(None, description="Chat ID для голосовых отправок")

    class Config:
        """Конфигурация Pydantic."""

        extra = "ignore"

