"""Безопасное хранение секретов через keyring (Windows Credential Manager)."""

import os
from typing import Optional

from kim_core.logging import logger

# Пробуем импортировать keyring
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    keyring = None
    logger.warning(
        "Библиотека keyring не установлена. "
        "Установите: pip install keyring. "
        "Секреты будут храниться только в переменных окружения."
    )

# Имя сервиса для keyring
SERVICE_NAME = "kim-ai-assistant"


def set_secret(secret_name: str, secret_value: str) -> None:
    """
    Сохраняет секрет в keyring.

    Args:
        secret_name: Имя секрета (например, "openrouter_api_key", "telegram_bot_token")
        secret_value: Значение секрета
    """
    if not KEYRING_AVAILABLE:
        logger.warning(f"keyring недоступен, секрет '{secret_name}' не сохранён в keyring")
        return

    try:
        keyring.set_password(SERVICE_NAME, secret_name, secret_value)
        logger.debug(f"Секрет '{secret_name}' сохранён в keyring")
    except Exception as e:
        logger.error(f"Ошибка сохранения секрета '{secret_name}' в keyring: {e}")
        raise


def get_secret(secret_name: str) -> Optional[str]:
    """
    Получает секрет из keyring.

    Args:
        secret_name: Имя секрета

    Returns:
        Значение секрета или None, если не найдено
    """
    if not KEYRING_AVAILABLE:
        logger.debug(f"keyring недоступен, секрет '{secret_name}' не может быть прочитан из keyring")
        return None

    try:
        secret = keyring.get_password(SERVICE_NAME, secret_name)
        if secret:
            logger.debug(f"Секрет '{secret_name}' прочитан из keyring")
        else:
            logger.debug(f"Секрет '{secret_name}' не найден в keyring")
        return secret
    except Exception as e:
        logger.warning(f"Ошибка чтения секрета '{secret_name}' из keyring: {e}")
        return None


def delete_secret(secret_name: str) -> None:
    """
    Удаляет секрет из keyring.

    Args:
        secret_name: Имя секрета
    """
    if not KEYRING_AVAILABLE:
        logger.debug(f"keyring недоступен, секрет '{secret_name}' не может быть удалён")
        return

    try:
        keyring.delete_password(SERVICE_NAME, secret_name)
        logger.debug(f"Секрет '{secret_name}' удалён из keyring")
    except Exception as e:
        logger.warning(f"Ошибка удаления секрета '{secret_name}' из keyring: {e}")


def load_secret_from_env_or_keyring(env_var_name: str, secret_name: str) -> Optional[str]:
    """
    Загружает секрет из переменной окружения или keyring.

    Логика:
    1. Если переменная окружения содержит значение:
       - Сохраняет его в keyring
       - Стирает из переменной окружения процесса
       - Возвращает значение
    2. Если переменная окружения пуста:
       - Пытается прочитать из keyring
       - Возвращает значение из keyring или None

    Args:
        env_var_name: Имя переменной окружения (например, "OPENROUTER_API_KEY")
        secret_name: Имя секрета в keyring (например, "openrouter_api_key")

    Returns:
        Значение секрета или None
    """
    # Читаем из переменной окружения
    env_value = os.getenv(env_var_name)

    if env_value and env_value.strip():
        # Если в окружении есть значение - сохраняем в keyring и стираем из процесса
        logger.info(f"Найден секрет '{secret_name}' в переменной окружения, сохраняю в keyring")
        try:
            set_secret(secret_name, env_value.strip())
            # Стираем из переменной окружения процесса (не влияет на системные переменные)
            os.environ.pop(env_var_name, None)
            logger.debug(f"Секрет '{secret_name}' удалён из переменной окружения процесса")
        except Exception as e:
            logger.error(f"Ошибка сохранения секрета '{secret_name}' в keyring: {e}")
            # Возвращаем значение из окружения, даже если не удалось сохранить
            return env_value.strip()

        return env_value.strip()

    # Если в окружении пусто - читаем из keyring
    logger.debug(f"Переменная окружения '{env_var_name}' пуста, читаю из keyring")
    keyring_value = get_secret(secret_name)

    if keyring_value:
        logger.info(f"Секрет '{secret_name}' загружен из keyring")
    else:
        logger.debug(f"Секрет '{secret_name}' не найден ни в окружении, ни в keyring")

    return keyring_value

