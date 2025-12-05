"""Тесты для модуля конфигурации."""

import os
import pytest
from unittest.mock import patch

from kim_core.config.settings import AppConfig, load_config


def test_load_config_dev_mode_without_critical_vars(monkeypatch):
    """Тест: в режиме dev конфиг загружается без критичных переменных."""
    # Очищаем все переменные окружения
    env_vars = {
        "MODE": "dev",
        "LOG_LEVEL": "INFO",
        # OPENROUTER_API_KEY и BOT_TOKEN не заданы
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    # Удаляем переменные, если они были установлены
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    
    # Конфиг должен загрузиться без ошибок
    config = load_config()
    
    assert config.mode == "dev"
    assert config.openrouter_api_key is None
    assert config.telegram_bot_token is None
    assert config.model_fast == "openai/gpt-3.5-turbo"  # значение по умолчанию


def test_load_config_prod_mode_without_api_key_raises_error(monkeypatch):
    """Тест: в режиме prod без OPENROUTER_API_KEY выбрасывается ошибка."""
    env_vars = {
        "MODE": "prod",
        "LOG_LEVEL": "INFO",
        # OPENROUTER_API_KEY не задан
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    
    # В режиме prod должна быть ошибка валидации
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY обязателен"):
        load_config()


def test_load_config_prod_mode_without_bot_token_raises_error(monkeypatch):
    """Тест: в режиме prod без BOT_TOKEN выбрасывается ошибка."""
    env_vars = {
        "MODE": "prod",
        "LOG_LEVEL": "INFO",
        "OPENROUTER_API_KEY": "test-key",
        # BOT_TOKEN не задан
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    
    # В режиме prod должна быть ошибка валидации
    with pytest.raises(ValueError, match="BOT_TOKEN обязателен"):
        load_config()


def test_load_config_prod_mode_with_all_vars_succeeds(monkeypatch):
    """Тест: в режиме prod со всеми переменными конфиг загружается."""
    env_vars = {
        "MODE": "prod",
        "LOG_LEVEL": "INFO",
        "OPENROUTER_API_KEY": "test-key-123",
        "BOT_TOKEN": "test-token-456",
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    config = load_config()
    
    assert config.mode == "prod"
    assert config.openrouter_api_key == "test-key-123"
    assert config.telegram_bot_token == "test-token-456"


def test_load_config_custom_mic_settings(monkeypatch):
    """Тест: настройки микрофона загружаются из переменных окружения."""
    env_vars = {
        "MODE": "dev",
        "LOG_LEVEL": "INFO",
        "MIC_DEVICE_INDEX": "1",
        "MIC_SAMPLE_RATE": "22050",
        "MIC_CHUNK_SIZE": "8000",
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    config = load_config()
    
    assert config.mic_device_index == 1
    assert config.mic_sample_rate == 22050
    assert config.mic_chunk_size == 8000


def test_load_config_default_values(monkeypatch):
    """Тест: значения по умолчанию устанавливаются корректно."""
    env_vars = {
        "MODE": "dev",
        "LOG_LEVEL": "INFO",
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    # Удаляем переменные, чтобы проверить значения по умолчанию
    monkeypatch.delenv("MIC_DEVICE_INDEX", raising=False)
    monkeypatch.delenv("MIC_SAMPLE_RATE", raising=False)
    monkeypatch.delenv("MIC_CHUNK_SIZE", raising=False)
    
    config = load_config()
    
    assert config.mic_device_index is None
    assert config.mic_sample_rate == 16000
    assert config.mic_chunk_size == 4000

