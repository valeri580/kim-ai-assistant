"""Модуль для работы с файлами."""

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
]

