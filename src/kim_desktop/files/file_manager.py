"""Модуль для управления файлами с поддержкой alias-директорий."""

import os
import shutil
from pathlib import Path
from typing import Optional

from kim_core.config.settings import AppConfig
from kim_core.logging import logger


class FileManagerError(Exception):
    """Базовое исключение для ошибок file_manager."""

    pass


class AliasNotFoundError(FileManagerError):
    """Исключение для несуществующего alias."""

    pass


class PathTraversalError(FileManagerError):
    """Исключение для попытки выхода за пределы разрешённой директории."""

    pass


# Маппинг alias-ов на стандартные директории Windows
# Поддерживаемые alias: downloads, desktop, documents
ALIAS_DIRECTORIES = {
    "downloads": None,  # Будет определена динамически
    "desktop": None,  # Будет определена динамически
    "documents": None,  # Будет определена динамически
}

# Русские названия для голосовых команд
ALIAS_RU_NAMES = {
    "downloads": ["загрузки", "скачал", "скачано", "downloads"],
    "desktop": ["рабочий стол", "desktop"],
    "documents": ["документы", "documents"],
}


def _get_user_directories() -> dict[str, Path]:
    """
    Получает стандартные директории пользователя Windows.

    Returns:
        Словарь с alias-ами и путями к директориям
    """
    user_profile = os.environ.get("USERPROFILE")
    if not user_profile:
        raise FileManagerError("Не удалось определить домашнюю директорию пользователя (USERPROFILE)")

    user_path = Path(user_profile)

    return {
        "downloads": user_path / "Downloads",
        "desktop": user_path / "Desktop",
        "documents": user_path / "Documents",
    }


def resolve_alias(alias: str) -> str:
    """
    Разрешает alias (включая русские названия) в стандартное имя.

    Args:
        alias: Имя alias или русское название

    Returns:
        str: Стандартное имя alias (downloads, desktop, documents)

    Raises:
        AliasNotFoundError: Если alias не найден
    """
    alias_lower = alias.lower().strip()

    # Проверяем прямое совпадение
    if alias_lower in ALIAS_DIRECTORIES:
        return alias_lower

    # Проверяем русские названия
    for standard_alias, ru_names in ALIAS_RU_NAMES.items():
        if alias_lower in ru_names:
            return standard_alias

    available = ", ".join(ALIAS_DIRECTORIES.keys())
    raise AliasNotFoundError(
        f"Alias '{alias}' не найден. Доступные alias: {available}"
    )


def get_alias_path(alias: str) -> Path:
    """
    Получает путь к директории по alias.

    Args:
        alias: Имя alias (downloads, desktop, documents) или русское название

    Returns:
        Path: Путь к директории

    Raises:
        AliasNotFoundError: Если alias не найден
    """
    # Разрешаем alias (включая русские названия)
    standard_alias = resolve_alias(alias)

    # Получаем стандартные директории
    directories = _get_user_directories()

    path = directories[standard_alias]

    # Создаём директорию, если её нет
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Создана директория для alias '{standard_alias}': {path}")
        except OSError as e:
            raise FileManagerError(f"Не удалось создать директорию для alias '{standard_alias}': {e}") from e

    return path


def safe_resolve_path(path: Path, root_dir: Path) -> Path:
    """
    Безопасно разрешает путь относительно корневой директории.

    Использует os.path.realpath для разрешения символических ссылок и нормализации пути.
    Проверяет, что результирующий путь находится внутри root_dir (защита от traversal).

    Args:
        path: Путь для разрешения (может быть относительным или абсолютным)
        root_dir: Корневая директория, за пределы которой нельзя выходить

    Returns:
        Path: Разрешённый и нормализованный путь

    Raises:
        PathTraversalError: Если путь выходит за пределы root_dir
        FileManagerError: Если путь не может быть разрешён
    """
    try:
        # Нормализуем root_dir
        root_dir_resolved = Path(os.path.realpath(str(root_dir)))
        if not root_dir_resolved.exists():
            raise FileManagerError(f"Корневая директория не существует: {root_dir_resolved}")

        # Если путь абсолютный, проверяем, что он внутри root_dir
        if path.is_absolute():
            path_resolved = Path(os.path.realpath(str(path)))
        else:
            # Относительный путь - разрешаем относительно root_dir
            combined = root_dir_resolved / path
            path_resolved = Path(os.path.realpath(str(combined)))

        # Проверяем, что разрешённый путь находится внутри root_dir
        # Используем is_relative_to для Python 3.9+, fallback для старых версий
        try:
            # Python 3.9+
            if not path_resolved.is_relative_to(root_dir_resolved):
                raise PathTraversalError(
                    f"Путь выходит за пределы корневой директории: {path_resolved} (корень: {root_dir_resolved})"
                )
        except AttributeError:
            # Python < 3.9
            try:
                path_resolved.relative_to(root_dir_resolved)
            except ValueError:
                raise PathTraversalError(
                    f"Путь выходит за пределы корневой директории: {path_resolved} (корень: {root_dir_resolved})"
                ) from None

        logger.debug(f"Безопасно разрешён путь: {path} -> {path_resolved} (корень: {root_dir_resolved})")
        return path_resolved

    except OSError as e:
        raise FileManagerError(f"Ошибка при разрешении пути {path}: {e}") from e


def put_file(source_path: Path, alias: str, filename: Optional[str] = None) -> Path:
    """
    Копирует файл в директорию, указанную через alias.

    Args:
        source_path: Путь к исходному файлу (может быть относительным или абсолютным)
        alias: Alias директории назначения (downloads, desktop, documents) или русское название
        filename: Имя файла в директории назначения (если None, используется исходное имя)

    Returns:
        Path: Путь к скопированному файлу

    Raises:
        FileManagerError: Если операция не удалась
        AliasNotFoundError: Если alias не найден
        PathTraversalError: Если путь небезопасен
    """
    # Разрешаем исходный путь (если относительный - относительно текущей директории)
    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path
    source_path = Path(os.path.realpath(str(source_path)))

    # Проверяем существование исходного файла
    if not source_path.exists():
        raise FileManagerError(f"Исходный файл не существует: {source_path}")

    if source_path.is_dir():
        raise FileManagerError(f"Исходный путь является директорией, а не файлом: {source_path}")

    # Получаем путь к директории назначения
    dest_dir = get_alias_path(alias)

    # Определяем имя файла назначения
    if filename:
        # Проверяем безопасность имени файла
        safe_filename = Path(filename).name  # Извлекаем только имя файла (без пути)
        dest_path = safe_resolve_path(Path(safe_filename), dest_dir)
    else:
        dest_path = dest_dir / source_path.name

    # Копируем файл
    try:
        logger.info(f"Копирование файла: {source_path} -> {dest_path}")
        shutil.copy2(source_path, dest_path)
        logger.info(f"Файл успешно скопирован: {dest_path}")
        return dest_path
    except OSError as e:
        raise FileManagerError(f"Ошибка при копировании файла: {e}") from e


def move_file(source_path: Path, alias: str, filename: Optional[str] = None) -> Path:
    """
    Перемещает файл в директорию, указанную через alias.

    Args:
        source_path: Путь к исходному файлу (может быть относительным или абсолютным)
        alias: Alias директории назначения (downloads, desktop, documents) или русское название
        filename: Имя файла в директории назначения (если None, используется исходное имя)

    Returns:
        Path: Путь к перемещённому файлу

    Raises:
        FileManagerError: Если операция не удалась
        AliasNotFoundError: Если alias не найден
        PathTraversalError: Если путь небезопасен
    """
    # Разрешаем исходный путь (если относительный - относительно текущей директории)
    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path
    source_path = Path(os.path.realpath(str(source_path)))

    # Проверяем существование исходного файла
    if not source_path.exists():
        raise FileManagerError(f"Исходный файл не существует: {source_path}")

    if source_path.is_dir():
        raise FileManagerError(f"Исходный путь является директорией, а не файлом: {source_path}")

    # Получаем путь к директории назначения
    dest_dir = get_alias_path(alias)

    # Определяем имя файла назначения
    if filename:
        # Проверяем безопасность имени файла
        safe_filename = Path(filename).name  # Извлекаем только имя файла (без пути)
        dest_path = safe_resolve_path(Path(safe_filename), dest_dir)
    else:
        dest_path = dest_dir / source_path.name

    # Перемещаем файл
    try:
        logger.info(f"Перемещение файла: {source_path} -> {dest_path}")
        shutil.move(str(source_path), str(dest_path))
        logger.info(f"Файл успешно перемещён: {dest_path}")
        return dest_path
    except OSError as e:
        raise FileManagerError(f"Ошибка при перемещении файла: {e}") from e


def list_files(alias: str, pattern: Optional[str] = None) -> list[Path]:
    """
    Возвращает список файлов в директории, указанной через alias.

    Args:
        alias: Alias директории (downloads, desktop, documents) или русское название
        pattern: Шаблон для фильтрации файлов (например, "*.txt", "*.pdf")

    Returns:
        list[Path]: Список путей к файлам

    Raises:
        FileManagerError: Если операция не удалась
        AliasNotFoundError: Если alias не найден
    """
    # Получаем путь к директории
    alias_dir = get_alias_path(alias)

    if not alias_dir.exists():
        logger.warning(f"Директория для alias '{alias}' не существует: {alias_dir}")
        return []

    try:
        if pattern:
            files = list(alias_dir.glob(pattern))
        else:
            # Получаем только файлы, исключая директории
            files = [f for f in alias_dir.iterdir() if f.is_file()]

        # Сортируем по имени
        files.sort(key=lambda p: p.name.lower())
        logger.info(f"Найдено {len(files)} файлов в alias '{alias}'")
        return files

    except OSError as e:
        raise FileManagerError(f"Ошибка при получении списка файлов: {e}") from e


def find_latest_file(alias: str, pattern: Optional[str] = None) -> Optional[Path]:
    """
    Находит последний изменённый файл в директории, указанной через alias.

    Args:
        alias: Alias директории (downloads, desktop, documents)
        pattern: Шаблон для фильтрации файлов (например, "*.txt", "*.pdf")

    Returns:
        Optional[Path]: Путь к последнему файлу или None, если файлов нет

    Raises:
        FileManagerError: Если операция не удалась
        AliasNotFoundError: Если alias не найден
    """
    files = list_files(alias, pattern)

    if not files:
        return None

    # Сортируем по времени модификации (последний изменённый - первый)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]

