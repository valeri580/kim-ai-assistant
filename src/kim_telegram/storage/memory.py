"""In-memory хранилище контекста диалогов."""

from typing import Dict, List


class InMemoryDialogStore:
    """Хранилище контекста диалогов в памяти."""

    def __init__(self) -> None:
        """Инициализирует хранилище."""
        self._dialogs: Dict[int, List[dict]] = {}

    def get_history(self, user_id: int) -> List[dict]:
        """
        Возвращает историю сообщений пользователя.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            List[dict]: Список сообщений в формате OpenAI
        """
        return self._dialogs.get(user_id, []).copy()

    def append_user_message(self, user_id: int, content: str) -> List[dict]:
        """
        Добавляет сообщение пользователя в историю.

        Args:
            user_id: ID пользователя Telegram
            content: Текст сообщения

        Returns:
            List[dict]: Обновлённая история сообщений
        """
        if user_id not in self._dialogs:
            self._dialogs[user_id] = []

        self._dialogs[user_id].append({"role": "user", "content": content})
        return self.get_history(user_id)

    def append_assistant_message(self, user_id: int, content: str) -> List[dict]:
        """
        Добавляет сообщение ассистента в историю.

        Args:
            user_id: ID пользователя Telegram
            content: Текст ответа ассистента

        Returns:
            List[dict]: Обновлённая история сообщений
        """
        if user_id not in self._dialogs:
            self._dialogs[user_id] = []

        self._dialogs[user_id].append({"role": "assistant", "content": content})
        return self.get_history(user_id)

    def reset(self, user_id: int) -> None:
        """
        Очищает историю диалога для пользователя.

        Args:
            user_id: ID пользователя Telegram
        """
        if user_id in self._dialogs:
            del self._dialogs[user_id]

