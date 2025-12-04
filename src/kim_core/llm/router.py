"""Маршрутизатор моделей LLM с учётом лимитов токенов."""

import re
from datetime import date
from typing import Optional

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

        # Выполняем запрос
        response, usage = await self.client.complete(
            cleaned_messages, model, max_tokens, temperature
        )

        # Обновляем счётчик токенов
        self._tokens_used_today += usage.total_tokens

        logger.info(
            f"Модель: {model}, "
            f"токены: {usage.total_tokens} "
            f"(сегодня: {self._tokens_used_today}/{self.config.token_budget_daily})"
        )

        return response

