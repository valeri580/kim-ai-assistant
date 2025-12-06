"""Модуль для работы с файлами."""

from kim_desktop.files.file_manager import (
    AliasNotFoundError,
    FileManagerError,
    PathTraversalError,
    find_latest_file,
    get_alias_path,
    list_files,
    move_file,
    put_file,
    resolve_alias,
    safe_resolve_path,
)
from kim_desktop.files.reader import (
    FileAccessError,
    FileTypeNotSupportedError,
    read_file_text,
    truncate_text,
)
from kim_desktop.files.summarizer import summarize_text_with_llm

__all__ = [
    "FileAccessError",
    "FileTypeNotSupportedError",
    "read_file_text",
    "truncate_text",
    "summarize_text_with_llm",
    "FileManagerError",
    "AliasNotFoundError",
    "PathTraversalError",
    "get_alias_path",
    "resolve_alias",
    "put_file",
    "move_file",
    "list_files",
    "find_latest_file",
    "safe_resolve_path",
]

