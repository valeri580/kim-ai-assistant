"""Модуль для отправки уведомлений в Telegram."""

from typing import Optional

from aiogram import Bot

from kim_core.logging import logger


class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram."""

    def __init__(self, bot_token: str, chat_id: int) -> None:
        """
        Инициализирует уведомитель.

        Args:
            bot_token: Токен Telegram бота
            chat_id: ID чата/пользователя для отправки уведомлений
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot: Optional[Bot] = Bot(token=bot_token)
        logger.info(f"TelegramNotifier инициализирован для chat_id={chat_id}")

    async def send_alert(self, text: str) -> None:
        """
        Отправляет уведомление в Telegram.

        Args:
            text: Текст уведомления
        """
        if not self.bot:
            logger.error("Bot не инициализирован")
            return

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text)
            logger.info(f"Уведомление отправлено в Telegram (chat_id={self.chat_id})")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления в Telegram: {e}")

    async def close(self) -> None:
        """Закрывает сессию бота."""
        if self.bot:
            try:
                await self.bot.session.close()
                logger.debug("Сессия Telegram бота закрыта")
            except Exception as e:
                logger.warning(f"Ошибка закрытия сессии бота: {e}")

