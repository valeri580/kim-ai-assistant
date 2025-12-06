"""Клиент для работы с OpenRouter API."""

import os
from dataclasses import dataclass
from typing import Optional

import httpx

from kim_core.config.settings import AppConfig
from kim_core.logging import logger


@dataclass
class LLMUsage:
    """Использование токенов и стоимость запроса."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: Optional[float] = None


class LLMError(Exception):
    """Базовое исключение для ошибок LLM."""

    pass


class OpenRouterClient:
    """Клиент для работы с OpenRouter API."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, config: AppConfig) -> None:
        """
        Инициализирует клиент OpenRouter.

        Args:
            config: Конфигурация приложения

        Raises:
            LLMError: Если отсутствует API-ключ
        """
        self.config = config

        if not config.openrouter_api_key:
            error_msg = "OPENROUTER_API_KEY не установлен"
            logger.error(error_msg)
            raise LLMError(error_msg)

    async def complete(
        self,
        messages: list[dict],
        model: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        timeout: float = 60.0,
        tools: Optional[list[dict]] = None,
    ) -> tuple[str, LLMUsage]:
        """
        Выполняет запрос к OpenRouter API.

        Args:
            messages: Список сообщений в формате OpenAI
            model: Имя модели
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура генерации (0.0-2.0)
            timeout: Таймаут запроса в секундах
            tools: Список инструментов для LLM (опционально)

        Returns:
            tuple[str, LLMUsage]: Ответ LLM и информация об использовании токенов

        Raises:
            LLMError: При ошибках запроса или обработки ответа
        """
        headers = {
            "Authorization": f"Bearer {self.config.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        # Опциональные заголовки для OpenRouter
        http_referer = os.getenv("HTTP_REFERER")
        x_title = os.getenv("X_TITLE")

        if http_referer:
            headers["HTTP-Referer"] = http_referer
        if x_title:
            headers["X-Title"] = x_title

        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        if tools:
            body["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(
                    f"Отправка запроса к OpenRouter: модель={model}, "
                    f"сообщений={len(messages)}"
                )

                response = await client.post(
                    self.BASE_URL,
                    headers=headers,
                    json=body,
                )

                response.raise_for_status()
                data = response.json()

                # Извлекаем ответ
                if "choices" not in data or not data["choices"]:
                    raise LLMError("Ответ не содержит choices")

                message = data["choices"][0].get("message", {})
                content = message.get("content", "")
                
                # Проверяем наличие tool_calls
                tool_calls = message.get("tool_calls")
                if tool_calls:
                    # Если есть tool_calls, возвращаем их вместо content
                    return {"tool_calls": tool_calls}, usage
                
                if not content:
                    raise LLMError("Ответ не содержит content или tool_calls")

                # Извлекаем информацию об использовании токенов
                usage_data = data.get("usage", {})
                usage = LLMUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                    cost=usage_data.get("total_cost") or usage_data.get("cost"),
                )

                logger.debug(
                    f"Получен ответ: токены={usage.total_tokens}, "
                    f"стоимость={usage.cost}"
                )

                # Возвращаем строку или dict с tool_calls
                if isinstance(content, dict):
                    return content, usage
                return content, usage

        except httpx.RequestError as e:
            error_msg = f"Ошибка сети при запросе к OpenRouter: {e}"
            logger.error(error_msg)
            raise LLMError(error_msg) from e

        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Ошибка HTTP {e.response.status_code} от OpenRouter: "
                f"{e.response.text}"
            )
            logger.error(error_msg)
            raise LLMError(error_msg) from e

        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Ошибка обработки ответа OpenRouter: {e}"
            logger.error(error_msg)
            raise LLMError(error_msg) from e

