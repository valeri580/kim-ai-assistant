"""Хранилище настроек с поддержкой профилей."""

import json
from pathlib import Path
from typing import Optional

from kim_core.config.runtime import RuntimeSettings, RuntimeSettingsStore
from kim_core.logging import logger

from kim_settings_panel.models import MODES, PROFILES, SCENARIOS, RuntimeSettingsUpdate


def get_mode_preset(mode: str) -> RuntimeSettings:
    """
    Возвращает RuntimeSettings с типовыми значениями для заданного режима.

    Режимы:
      - "voice_assistant": голосовой ассистент включён
      - "telegram_only": только Telegram-бот
      - "offline": полностью офлайн режим

    Args:
        mode: Имя режима (voice_assistant, telegram_only, offline)

    Returns:
        RuntimeSettings: Настройки режима

    Raises:
        ValueError: Если режим не найден
    """
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}. Available: {MODES}")

    if mode == "voice_assistant":
        return RuntimeSettings(
            mode="voice_assistant",
            enable_voice_assistant=True,
            enable_web_search=True,
            local_only=False,
        )
    elif mode == "telegram_only":
        return RuntimeSettings(
            mode="telegram_only",
            enable_voice_assistant=False,
            enable_web_search=False,
            local_only=False,
        )
    elif mode == "offline":
        return RuntimeSettings(
            mode="offline",
            enable_voice_assistant=True,
            enable_web_search=False,
            local_only=True,
        )
    else:
        raise ValueError(f"Mode preset not implemented: {mode}")


def get_profile_preset(profile: str) -> RuntimeSettings:
    """
    Возвращает RuntimeSettings с типовыми значениями для заданного профиля.

    Профили:
      - "quality": максимум качества, можно жертвовать скоростью
      - "performance": максимально лёгкий/быстрый режим
      - "balanced": что-то среднее

    Args:
        profile: Имя профиля (quality, balanced, performance)

    Returns:
        RuntimeSettings: Настройки профиля

    Raises:
        ValueError: Если профиль не найден
    """
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}. Available: {PROFILES}")

    if profile == "quality":
        return RuntimeSettings(
            profile="quality",
            local_only=False,
            model_fast="openai/gpt-4o-mini",  # Более качественная быстрая модель
            model_smart="openai/gpt-4o",  # Максимально качественная модель
            token_budget_daily=200000,
            tts_rate=2,  # Немного медленнее для лучшей разборчивости
            tts_volume=100,
        )
    elif profile == "performance":
        return RuntimeSettings(
            profile="performance",
            local_only=False,
            model_fast="openai/gpt-3.5-turbo",  # Самая быстрая/дешёвая
            model_smart="openai/gpt-3.5-turbo",  # Та же, что fast
            token_budget_daily=20000,  # Минимальный лимит
            tts_rate=5,  # Быстрее
            tts_volume=90,
        )
    elif profile == "balanced":
        return RuntimeSettings(
            profile="balanced",
            local_only=False,
            model_fast="openai/gpt-4o-mini",
            model_smart="openai/gpt-4-turbo",
            token_budget_daily=50000,
            tts_rate=3,  # Средняя скорость
            tts_volume=100,
        )
    else:
        raise ValueError(f"Profile preset not implemented: {profile}")


class SettingsStore(RuntimeSettingsStore):
    """Расширенное хранилище настроек с поддержкой профилей."""

    def save(self, settings: RuntimeSettings) -> None:
        """
        Сохраняет настройки в JSON-файл.

        Args:
            settings: Настройки для сохранения
        """
        # Создаём директорию, если её нет
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Сохраняем в JSON
        # Используем model_dump для Pydantic v2 или dict() для v1
        try:
            settings_dict = settings.model_dump(exclude_none=True)
        except AttributeError:
            # Fallback для Pydantic v1
            settings_dict = settings.dict(exclude_none=True)
        
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(settings_dict, f, indent=2, ensure_ascii=False)

        self._current_settings = settings
        self._update_mtime()
        logger.info(f"Runtime settings saved to {self.settings_path}")

    def apply_profile(self, profile: str) -> RuntimeSettings:
        """
        Применяет пресет профиля.

        Профиль применяется как полный override для ключевых полей.
        Пользователь может потом донастроить значения вручную.

        Args:
            profile: Имя профиля

        Returns:
            RuntimeSettings: Обновлённые настройки

        Raises:
            ValueError: Если профиль не найден
        """
        if profile not in PROFILES:
            raise ValueError(f"Unknown profile: {profile}. Available: {PROFILES}")

        # Получаем пресет профиля
        preset = get_profile_preset(profile)

        # Сохраняем пресет
        self.save(preset)

        logger.info(f"Profile '{profile}' applied")
        return preset

    def update(self, patch: RuntimeSettingsUpdate) -> RuntimeSettings:
        """
        Обновляет настройки частично.

        Если в patch указан profile, сначала применяется профиль,
        затем накладываются остальные поля из patch.

        Args:
            patch: Частичное обновление настроек

        Returns:
            RuntimeSettings: Обновлённые настройки
        """
        # Если указан профиль, применяем его сначала
        if patch.profile is not None:
            if patch.profile not in PROFILES:
                raise ValueError(f"Unknown profile: {patch.profile}. Available: {PROFILES}")

            # Применяем профиль
            current = self.apply_profile(patch.profile)
        else:
            # Загружаем текущие настройки
            current = self.load()

        # Создаём словарь для обновления
        try:
            update_dict = current.model_dump(exclude_none=True)
        except AttributeError:
            # Fallback для Pydantic v1
            update_dict = current.dict(exclude_none=True)

        # Применяем остальные поля из patch (исключая profile, т.к. он уже применён)
        try:
            patch_dict = patch.model_dump(exclude_none=True, exclude={"profile"})
        except AttributeError:
            # Fallback для Pydantic v1
            patch_dict = patch.dict(exclude_none=True, exclude={"profile"})
        update_dict.update(patch_dict)

        # Если profile был указан, сохраняем его в настройках
        if patch.profile is not None:
            update_dict["profile"] = patch.profile

        # Создаём обновлённые настройки
        updated = RuntimeSettings(**update_dict)

        # Сохраняем
        self.save(updated)

        logger.info(f"Settings updated: {list(patch_dict.keys())}")
        return updated

    def apply_mode(self, mode: str) -> RuntimeSettings:
        """
        Применяет пресет режима.

        Режим применяется как полный override для ключевых полей режима.
        Пользователь может потом донастроить значения вручную.

        Args:
            mode: Имя режима

        Returns:
            RuntimeSettings: Обновлённые настройки

        Raises:
            ValueError: Если режим не найден
        """
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}. Available: {MODES}")

        # Получаем пресет режима
        preset = get_mode_preset(mode)

        # Загружаем текущие настройки и объединяем с пресетом режима
        current = self.load()
        try:
            current_dict = current.model_dump(exclude_none=True)
        except AttributeError:
            current_dict = current.dict(exclude_none=True)

        try:
            preset_dict = preset.model_dump(exclude_none=True)
        except AttributeError:
            preset_dict = preset.dict(exclude_none=True)

        # Объединяем: пресет режима перезаписывает соответствующие поля
        current_dict.update(preset_dict)
        current_dict["mode"] = mode

        # Создаём обновлённые настройки
        updated = RuntimeSettings(**current_dict)

        # Сохраняем
        self.save(updated)

        logger.info(f"Mode '{mode}' applied")
        return updated

    def apply_scenario(self, scenario_id: str) -> RuntimeSettings:
        """
        Применяет готовый сценарий.

        Сценарий объединяет mode + profile + дополнительные настройки.
        Последовательность:
          1) применяется mode (apply_mode),
          2) применяется profile (apply_profile),
          3) накладываются дополнительные настройки для сценария.

        Args:
            scenario_id: Идентификатор сценария

        Returns:
            RuntimeSettings: Обновлённые настройки

        Raises:
            ValueError: Если сценарий не найден
        """
        if scenario_id not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_id}. Available: {list(SCENARIOS.keys())}")

        preset = SCENARIOS[scenario_id]
        mode = preset["mode"]
        profile = preset["profile"]

        logger.info(f"Applying scenario '{scenario_id}': mode={mode}, profile={profile}")

        # 1) Применяем режим
        settings_after_mode = self.apply_mode(mode)

        # 2) Применяем профиль
        settings_after_profile = self.apply_profile(profile)

        # 3) Дополнительные настройки для конкретного сценария
        try:
            current_dict = settings_after_profile.model_dump(exclude_none=True)
        except AttributeError:
            current_dict = settings_after_profile.dict(exclude_none=True)

        if scenario_id == "home_voice_assistant":
            # Домашний голосовой ассистент: максимум возможностей
            current_dict["local_only"] = False
            current_dict["enable_voice_assistant"] = True
            current_dict["enable_web_search"] = True
            # Если token_budget_daily не задан профилем, устанавливаем высокий лимит
            if current_dict.get("token_budget_daily") is None:
                current_dict["token_budget_daily"] = 200000

        elif scenario_id == "light_telegram_helper":
            # Лёгкий Telegram-помощник: минимум ресурсов
            current_dict["enable_voice_assistant"] = False
            current_dict["enable_web_search"] = False
            current_dict["local_only"] = False
            # Уменьшаем лимит токенов для экономии
            if current_dict.get("token_budget_daily", 0) > 20000:
                current_dict["token_budget_daily"] = 20000

        elif scenario_id == "offline_desktop_assistant":
            # Полностью офлайн: без интернета
            current_dict["local_only"] = True
            current_dict["enable_voice_assistant"] = True
            current_dict["enable_web_search"] = False
            # Очищаем модели, т.к. LLM не используется
            current_dict.pop("model_fast", None)
            current_dict.pop("model_smart", None)
            current_dict.pop("token_budget_daily", None)

        # Устанавливаем scenario_id
        current_dict["scenario"] = scenario_id
        current_dict["mode"] = mode
        current_dict["profile"] = profile

        # Создаём финальные настройки
        final_settings = RuntimeSettings(**current_dict)

        # Сохраняем
        self.save(final_settings)

        logger.info(
            f"Scenario '{scenario_id}' applied: "
            f"mode={final_settings.mode}, profile={final_settings.profile}, "
            f"local_only={final_settings.local_only}, "
            f"enable_voice_assistant={final_settings.enable_voice_assistant}, "
            f"enable_web_search={final_settings.enable_web_search}"
        )

        return final_settings

