"""Runtime-настройки (динамические настройки, изменяемые без перезапуска)."""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from kim_core.config.settings import AppConfig
from kim_core.logging import logger


class RuntimeSettings(BaseModel):
    """Модель runtime-настроек (изменяемых без перезапуска)."""

    # Сценарий и профиль
    scenario: Optional[str] = Field(None, description="Имя текущего сценария (home_voice_assistant, light_telegram_helper, offline_desktop_assistant)")
    profile: Optional[str] = Field(None, description="Имя текущего профиля (quality, balanced, performance)")
    mode: Optional[str] = Field(None, description="Режим работы (voice_assistant, telegram_only, offline)")

    # Режим работы
    local_only: Optional[bool] = Field(None, description="Режим только локально (без LLM)")
    enable_voice_assistant: Optional[bool] = Field(None, description="Включить голосовой ассистент")
    enable_web_search: Optional[bool] = Field(None, description="Включить веб-поиск")

    # Настройки голоса (TTS)
    tts_rate: Optional[int] = Field(None, description="Скорость речи (-10 до 10 для COM)")
    tts_volume: Optional[int] = Field(None, description="Громкость (0-100)")

    # Настройки LLM
    model_fast: Optional[str] = Field(None, description="Быстрая модель LLM")
    model_smart: Optional[str] = Field(None, description="Умная модель LLM")
    token_budget_daily: Optional[int] = Field(None, description="Дневной лимит токенов")

    # Настройки микрофона (опционально, для MVP можно не применять на лету)
    mic_device_index: Optional[int] = Field(None, description="Индекс микрофона")
    mic_sample_rate: Optional[int] = Field(None, description="Частота дискретизации микрофона")
    mic_chunk_size: Optional[int] = Field(None, description="Размер чанка микрофона")

    # Настройки Telegram
    voice_telegram_chat_id: Optional[int] = Field(None, description="Chat ID для голосовых отправок")

    # Пороги диагностики ПК
    cpu_warn: Optional[float] = Field(None, description="Порог предупреждения для загрузки CPU (в процентах)")
    ram_warn: Optional[float] = Field(None, description="Порог предупреждения для использования RAM (в процентах)")
    disk_warn: Optional[float] = Field(None, description="Порог предупреждения для использования диска (в процентах)")
    temp_warn: Optional[float] = Field(None, description="Порог предупреждения для температуры (в градусах Цельсия)")

    class Config:
        """Конфигурация Pydantic."""

        extra = "ignore"  # Игнорируем лишние поля в JSON


class RuntimeSettingsStore:
    """Хранилище runtime-настроек с поддержкой автообновления."""

    def __init__(self, settings_path: str | Path) -> None:
        """
        Инициализирует хранилище.

        Args:
            settings_path: Путь к JSON-файлу с runtime-настройками
        """
        self.settings_path = Path(settings_path)
        self._last_mtime: Optional[float] = None
        self._current_settings: Optional[RuntimeSettings] = None

    def load(self) -> RuntimeSettings:
        """
        Загружает runtime-настройки из файла.

        Returns:
            RuntimeSettings: Загруженные настройки

        Raises:
            FileNotFoundError: Если файл не существует
            ValueError: Если JSON некорректен или валидация не прошла
        """
        if not self.settings_path.exists():
            logger.debug(f"Runtime settings file not found: {self.settings_path}, using defaults")
            self._current_settings = RuntimeSettings()
            self._update_mtime()
            return self._current_settings

        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            settings = RuntimeSettings(**data)
            self._current_settings = settings
            self._update_mtime()

            logger.debug(f"Runtime settings loaded from {self.settings_path}")
            return settings

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in runtime settings file: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load runtime settings: {e}") from e

    def _update_mtime(self) -> None:
        """Обновляет сохранённое время модификации файла."""
        if self.settings_path.exists():
            try:
                self._last_mtime = os.path.getmtime(self.settings_path)
            except OSError:
                self._last_mtime = None
        else:
            self._last_mtime = None

    def has_changed(self) -> bool:
        """
        Проверяет, изменился ли файл настроек.

        Returns:
            bool: True, если файл изменился или это первая проверка (и файл существует)
        """
        if not self.settings_path.exists():
            return False

        try:
            current_mtime = os.path.getmtime(self.settings_path)
        except OSError:
            return False

        if self._last_mtime is None:
            # Первая проверка - сохраняем mtime, но не считаем это изменением
            self._last_mtime = current_mtime
            return False

        if current_mtime != self._last_mtime:
            return True

        return False

    def reload_if_changed(self) -> Optional[RuntimeSettings]:
        """
        Перезагружает настройки, если файл изменился.

        Returns:
            Optional[RuntimeSettings]: Новые настройки, если файл изменился, иначе None

        При ошибках чтения/валидации логирует предупреждение и возвращает None,
        сохраняя текущие настройки.
        """
        if not self.has_changed():
            return None

        try:
            new_settings = self.load()
            logger.info(f"Runtime settings reloaded from {self.settings_path}")
            return new_settings

        except ValueError as e:
            logger.warning(
                f"Failed to reload runtime settings: {e}. "
                f"Сохраняю предыдущие настройки."
            )
            return None
        except Exception as e:
            logger.warning(
                f"Unexpected error reloading runtime settings: {e}. "
                f"Сохраняю предыдущие настройки."
            )
            return None


def merge_config_with_runtime(
    base_config: AppConfig, runtime_settings: RuntimeSettings
) -> AppConfig:
    """
    Объединяет базовую конфигурацию с runtime-настройками.

    Runtime-настройки переопределяют значения из base_config только если они не None.

    Args:
        base_config: Базовая конфигурация из .env
        runtime_settings: Runtime-настройки из JSON

    Returns:
        AppConfig: Объединённая конфигурация
    """
    # Создаём копию базовой конфигурации
    merged_dict = {
        "mode": base_config.mode,
        "log_level": base_config.log_level,
        "openrouter_api_key": base_config.openrouter_api_key,
        "telegram_bot_token": base_config.telegram_bot_token,
        "model_fast": base_config.model_fast,
        "model_smart": base_config.model_smart,
        "token_budget_daily": base_config.token_budget_daily,
        "local_only": base_config.local_only,
        "cpu_warn": base_config.cpu_warn,
        "ram_warn": base_config.ram_warn,
        "disk_warn": base_config.disk_warn,
        "temp_warn": base_config.temp_warn,
        "alerts_chat_id": base_config.alerts_chat_id,
        "diagnostics_interval_seconds": base_config.diagnostics_interval_seconds,
        "mic_device_index": base_config.mic_device_index,
        "mic_sample_rate": base_config.mic_sample_rate,
        "mic_chunk_size": base_config.mic_chunk_size,
        "reminders_db_path": base_config.reminders_db_path,
        "reminders_interval_seconds": base_config.reminders_interval_seconds,
        "serpapi_key": base_config.serpapi_key,
        "web_search_max_results": base_config.web_search_max_results,
        "file_whitelist_dirs": base_config.file_whitelist_dirs,
        "file_max_size_mb": base_config.file_max_size_mb,
        "file_summary_max_chars": base_config.file_summary_max_chars,
        "voice_telegram_chat_id": base_config.voice_telegram_chat_id,
    }

    # Применяем runtime-настройки (только если они не None)
    if runtime_settings.local_only is not None:
        merged_dict["local_only"] = runtime_settings.local_only

    if runtime_settings.model_fast is not None:
        merged_dict["model_fast"] = runtime_settings.model_fast

    if runtime_settings.model_smart is not None:
        merged_dict["model_smart"] = runtime_settings.model_smart

    if runtime_settings.token_budget_daily is not None:
        merged_dict["token_budget_daily"] = runtime_settings.token_budget_daily

    if runtime_settings.mic_device_index is not None:
        merged_dict["mic_device_index"] = runtime_settings.mic_device_index

    if runtime_settings.mic_sample_rate is not None:
        merged_dict["mic_sample_rate"] = runtime_settings.mic_sample_rate

    if runtime_settings.mic_chunk_size is not None:
        merged_dict["mic_chunk_size"] = runtime_settings.mic_chunk_size

    if runtime_settings.voice_telegram_chat_id is not None:
        merged_dict["voice_telegram_chat_id"] = runtime_settings.voice_telegram_chat_id

    # Пороги диагностики ПК
    if runtime_settings.cpu_warn is not None:
        merged_dict["cpu_warn"] = runtime_settings.cpu_warn
    if runtime_settings.ram_warn is not None:
        merged_dict["ram_warn"] = runtime_settings.ram_warn
    if runtime_settings.disk_warn is not None:
        merged_dict["disk_warn"] = runtime_settings.disk_warn
    if runtime_settings.temp_warn is not None:
        merged_dict["temp_warn"] = runtime_settings.temp_warn

    # Создаём новый AppConfig с объединёнными значениями
    return AppConfig(**merged_dict)

