"""Тесты для модуля LLM Router."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from kim_core.config.settings import AppConfig
from kim_core.llm.router import BudgetExceededError, LLMRouter


@pytest.fixture
def mock_config():
    """Фикстура для создания тестовой конфигурации."""
    return AppConfig(
        mode="dev",
        log_level="INFO",
        openrouter_api_key="test-key",
        telegram_bot_token=None,
        model_fast="openai/gpt-3.5-turbo",
        model_smart="openai/gpt-4-turbo",
        token_budget_daily=1000,
    )


@pytest.fixture
def mock_client():
    """Фикстура для создания мок-клиента OpenRouter."""
    client = AsyncMock()
    usage = MagicMock()
    usage.total_tokens = 100
    client.complete = AsyncMock(return_value=("Test response", usage))
    return client


def test_choose_model_default_fast_model(mock_config):
    """Тест: по умолчанию выбирается быстрая модель."""
    router = LLMRouter(mock_config)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Привет, как дела?"},
    ]
    
    model, cleaned_messages = router._choose_model(messages)
    
    assert model == mock_config.model_fast
    assert cleaned_messages == messages


def test_choose_model_smart_model_with_trigger(mock_config):
    """Тест: при наличии триггера выбирается умная модель и удаляется триггер."""
    router = LLMRouter(mock_config)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "реши это gpt-5, объясни квантовую физику"},
    ]
    
    model, cleaned_messages = router._choose_model(messages)
    
    assert model == mock_config.model_smart
    # Триггерная фраза должна быть удалена
    assert "реши это gpt-5" not in cleaned_messages[-1]["content"].lower()
    assert "квантовую физику" in cleaned_messages[-1]["content"].lower()


def test_choose_model_smart_model_with_quality_trigger(mock_config):
    """Тест: триггер 'режим качества' переключает на умную модель."""
    router = LLMRouter(mock_config)
    
    messages = [
        {"role": "user", "content": "Нужно проанализировать режим качества этот документ"},
    ]
    
    model, cleaned_messages = router._choose_model(messages)
    
    assert model == mock_config.model_smart
    assert "режим качества" not in cleaned_messages[-1]["content"].lower()


def test_token_budget_exceeded_raises_error(mock_config, mock_client):
    """Тест: при превышении лимита токенов выбрасывается BudgetExceededError."""
    router = LLMRouter(mock_config, mock_client)
    router._tokens_used_today = mock_config.token_budget_daily  # Лимит исчерпан
    
    messages = [
        {"role": "user", "content": "Тест"},
    ]
    
    with pytest.raises(BudgetExceededError):
        import asyncio
        asyncio.run(router.run(messages))


@pytest.mark.asyncio
async def test_token_budget_check_before_request(mock_config, mock_client):
    """Тест: лимит токенов проверяется перед запросом."""
    router = LLMRouter(mock_config, mock_client)
    router._tokens_used_today = mock_config.token_budget_daily  # Лимит исчерпан
    
    messages = [
        {"role": "user", "content": "Тест"},
    ]
    
    with pytest.raises(BudgetExceededError, match="Превышен дневной лимит"):
        await router.run(messages)
    
    # Клиент не должен быть вызван, если лимит превышен
    mock_client.complete.assert_not_called()


@pytest.mark.asyncio
async def test_tokens_counted_after_request(mock_config, mock_client):
    """Тест: токены учитываются после успешного запроса."""
    router = LLMRouter(mock_config, mock_client)
    
    initial_tokens = router._tokens_used_today
    usage = MagicMock()
    usage.total_tokens = 150
    mock_client.complete = AsyncMock(return_value=("Response", usage))
    
    messages = [
        {"role": "user", "content": "Тест"},
    ]
    
    await router.run(messages)
    
    assert router._tokens_used_today == initial_tokens + 150

