"""Маршрутизатор моделей LLM с учётом лимитов токенов."""

import json
import re
from datetime import date
from typing import Any, Optional

from kim_core.config.settings import AppConfig
from kim_core.llm.openrouter_client import LLMError, OpenRouterClient, LLMUsage
from kim_core.logging import logger


class BudgetExceededError(LLMError):
    """Исключение при превышении дневного лимита токенов."""

    pass


class LLMRouter:
    """Маршрутизатор моделей LLM с управлением лимитами."""

    # Триггеры для перехода на умную модель
    SMART_TRIGGERS = [
        r"реши это gpt-5",
        r"режим качества",
        r"нужен максимальный анализ",
    ]

    def __init__(
        self, config: AppConfig, client: Optional[OpenRouterClient] = None
    ) -> None:
        """
        Инициализирует маршрутизатор.

        Args:
            config: Конфигурация приложения
            client: Клиент OpenRouter (если None, создаётся новый)
        """
        self.config = config
        self.client = client or OpenRouterClient(config)
        self._current_date = date.today()
        self._tokens_used_today = 0
        self._tools: list[Any] = []  # Список зарегистрированных инструментов

    def _reset_if_new_day(self) -> None:
        """Сбрасывает счётчик токенов, если дата сменилась."""
        today = date.today()
        if today > self._current_date:
            logger.info(
                f"Новый день: сброс счётчика токенов "
                f"(было использовано {self._tokens_used_today})"
            )
            self._current_date = today
            self._tokens_used_today = 0

    def _choose_model(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """
        Выбирает модель на основе триггеров в сообщениях.

        Args:
            messages: Список сообщений

        Returns:
            tuple[str, list[dict]]: Имя модели и очищенные сообщения
        """
        # По умолчанию используем быструю модель
        model = self.config.model_fast
        cleaned_messages = messages.copy()

        # Проверяем последнее пользовательское сообщение на триггеры
        if messages:
            last_message = messages[-1]
            if last_message.get("role") == "user":
                content = last_message.get("content", "").lower()

                # Проверяем наличие триггеров
                for trigger in self.SMART_TRIGGERS:
                    if re.search(trigger, content, re.IGNORECASE):
                        logger.info(
                            f"Обнаружен триггер '{trigger}': "
                            f"переключение на умную модель"
                        )
                        model = self.config.model_smart

                        # Удаляем триггерные фразы из последнего сообщения
                        cleaned_content = last_message.get("content", "")
                        for trig in self.SMART_TRIGGERS:
                            cleaned_content = re.sub(
                                trig, "", cleaned_content, flags=re.IGNORECASE
                            )
                        cleaned_content = re.sub(r"\s+", " ", cleaned_content).strip()

                        cleaned_messages[-1] = {
                            **last_message,
                            "content": cleaned_content,
                        }
                        break

        return model, cleaned_messages

    def register_tool(self, tool: Any) -> None:
        """
        Регистрирует инструмент для использования LLM.

        Args:
            tool: Инструмент с методами name, description, request_model, run
        """
        self._tools.append(tool)
        logger.info(f"Зарегистрирован инструмент: {tool.name}")

    def _get_tools_schema(self) -> list[dict]:
        """
        Формирует схему инструментов для OpenAI API.

        Returns:
            Список схем инструментов
        """
        tools_schema = []
        for tool in self._tools:
            # Получаем схему модели запроса из Pydantic
            request_schema = tool.request_model.model_json_schema()
            
            tools_schema.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": request_schema,
                },
            })
        return tools_schema

    async def _execute_tool_call(self, tool_call: dict) -> dict:
        """
        Выполняет вызов инструмента.

        Args:
            tool_call: Словарь с информацией о вызове инструмента

        Returns:
            Результат выполнения инструмента
        """
        function_name = tool_call.get("function", {}).get("name")
        function_args = tool_call.get("function", {}).get("arguments", "{}")
        
        # Ищем инструмент по имени
        tool = None
        for t in self._tools:
            if t.name == function_name:
                tool = t
                break
        
        if not tool:
            logger.warning(f"Инструмент '{function_name}' не найден")
            return {"error": f"Инструмент '{function_name}' не найден"}

        try:
            # Парсим аргументы (JSON-строка)
            args = json.loads(function_args)
            
            # Создаём запрос через Pydantic модель
            request = tool.request_model(**args)
            
            # Выполняем инструмент
            result = await tool.run(request)
            
            logger.info(f"Инструмент '{function_name}' выполнен успешно")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка выполнения инструмента '{function_name}': {e}")
            return {"error": str(e)}

    async def run(
        self,
        messages: list[dict],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Выполняет запрос к LLM с маршрутизацией и учётом лимитов.

        Args:
            messages: Список сообщений в формате OpenAI
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура генерации

        Returns:
            str: Ответ LLM

        Raises:
            BudgetExceededError: При превышении дневного лимита токенов
            LLMError: При ошибках запроса к LLM
        """
        self._reset_if_new_day()

        # Выбираем модель
        model, cleaned_messages = self._choose_model(messages)

        # Проверяем лимит токенов
        if self._tokens_used_today >= self.config.token_budget_daily:
            error_msg = (
                f"Превышен дневной лимит токенов: "
                f"{self._tokens_used_today}/{self.config.token_budget_daily}"
            )
            logger.warning(error_msg)
            raise BudgetExceededError(error_msg)

        # Формируем схему инструментов, если они есть
        tools_schema = self._get_tools_schema() if self._tools else None

        # Выполняем запрос (может вернуть tool_calls)
        response, usage = await self.client.complete(
            cleaned_messages, model, max_tokens, temperature, tools=tools_schema
        )

        # Обновляем счётчик токенов
        self._tokens_used_today += usage.total_tokens

        # Если ответ содержит tool_calls, выполняем их
        if isinstance(response, dict) and "tool_calls" in response:
            tool_calls = response["tool_calls"]
            logger.info(f"Обнаружены вызовы инструментов: {len(tool_calls)}")
            
            # Выполняем все вызовы инструментов
            tool_results = []
            for tool_call in tool_calls:
                result = await self._execute_tool_call(tool_call)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": str(result),
                })
            
            # Добавляем результаты инструментов в сообщения
            cleaned_messages.extend(tool_results)
            
            # Выполняем повторный запрос с результатами инструментов
            final_response, final_usage = await self.client.complete(
                cleaned_messages, model, max_tokens, temperature, tools=tools_schema
            )
            
            # Обновляем счётчик токенов с учётом второго запроса
            self._tokens_used_today += final_usage.total_tokens
            
            logger.info(
                f"Модель: {model}, "
                f"токены: {usage.total_tokens + final_usage.total_tokens} "
                f"(сегодня: {self._tokens_used_today}/{self.config.token_budget_daily})"
            )
            
            # Возвращаем финальный ответ (не tool_calls)
            if isinstance(final_response, dict) and "tool_calls" in final_response:
                # Если снова tool_calls, возвращаем ошибку (ограничиваем рекурсию)
                return "Произошла ошибка: модель запросила слишком много инструментов."
            return final_response

        logger.info(
            f"Модель: {model}, "
            f"токены: {usage.total_tokens} "
            f"(сегодня: {self._tokens_used_today}/{self.config.token_budget_daily})"
        )

        return response

